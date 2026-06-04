"""
解忧信箱 API 服务
启动: cd backend && python main.py
"""
import os
import re
import random
import string
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Query, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from models import SessionLocal, engine, Base, Letter, Code, UserProfile, Question, Answer

# 建表
Base.metadata.create_all(bind=engine)

app = FastAPI(title="解忧信箱 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ========== 管理员安全配置 ==========
# 管理员安全码
ADMIN_PASSWORD = "zoutao147"  

# 运行时生成的 token 列表，用于验证已登录的管理员
_admin_tokens: set[str] = set()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def verify_admin(request: Request):
    """验证管理员 token，用于保护管理 API"""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth[7:]
        if token in _admin_tokens:
            return True
    raise HTTPException(status_code=401, detail="未授权访问，请先输入安全码")


# ========== 违规词过滤（基础版） ==========

SENSITIVE_WORDS = [
    "微信", "加我", "私聊", "转账", "红包", "付款", "支付宝",
    "赌博", "彩票", "刷单", "兼职", "贷款", "信用卡",
    "自杀", "自残", "去死", "不想活", "割腕",
    "黄赌毒", "色情", "裸聊", "约炮", "暴力", "QQ"
]

def contains_sensitive(text: str) -> list[str]:
    """检查文本是否包含违规词，返回匹配到的词列表"""
    found = []
    text_lower = text.lower()
    for word in SENSITIVE_WORDS:
        if word in text_lower:
            found.append(word)
    return found


# ========== Schemas ==========

class RedeemRequest(BaseModel):
    code: str
    age: int = 0  # 用户年龄，0表示未提供


class LetterCreate(BaseModel):
    type: str = "healing"
    title: Optional[str] = None
    content: str
    signature: str = "—— 你的解忧人"


class LetterUpdate(BaseModel):
    type: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    signature: Optional[str] = None


class CodeGenerateRequest(BaseModel):
    letter_id: int
    prefix: str = "XJ"
    quantity: int = 10
    batch_id: Optional[str] = None


class AnswerSubmitRequest(BaseModel):
    code: str  # 回答者的兑换码
    question_id: int  # 回答的问题ID
    answer_content: str  # 回答内容
    new_question: Optional[str] = None  # 可选的新问题


class AnswerQueryRequest(BaseModel):
    code: str  # 提问者的兑换码


class ReviewRequest(BaseModel):
    action: str  # approve / reject


class AdminLoginRequest(BaseModel):
    password: str


# ========== 管理员登录 API ==========

@app.post("/api/admin/login")
def admin_login(req: AdminLoginRequest):
    if req.password == ADMIN_PASSWORD:
        token = secrets.token_urlsafe(32)
        _admin_tokens.add(token)
        return {"success": True, "token": token}
    return {"success": False, "error": "安全码错误"}


# ========== 公开 API：兑换 ==========

@app.post("/api/redeem")
def redeem(req: RedeemRequest, db: Session = Depends(get_db)):
    code_str = req.code.strip().upper()

    # 先检查兑换码状态，再校验年龄
    code = db.query(Code).filter(Code.code == code_str).first()
    if not code:
        return {"success": False, "error": "兑换码无效，请检查后重试"}
    if code.status == "used":
        return {
            "success": False,
            "error": "already_used",
            "message": "该兑换码已使用过，可点击「查看我收到的回答」查询回答",
        }
    if code.status == "expired":
        return {"success": False, "error": "该兑换码已过期"}

    age = req.age
    if age < 1 or age > 150:
        return {"success": False, "error": "请输入有效的年龄"}

    # 生成昵称：兑换码后3位 + "用户"
    suffix = code_str[-3:] if len(code_str) >= 3 else code_str
    nickname = f"{suffix}用户"

    # 创建用户档案
    profile = UserProfile(code=code_str, nickname=nickname, age=age)
    db.add(profile)

    # 核销兑换码
    code.status = "used"
    code.used_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(code)

    letter = code.letter
    return {
        "success": True,
        "already_used": False,
        "letter": {
            "id": letter.id,
            "type": letter.type,
            "title": letter.title,
            "content": letter.content,
            "signature": letter.signature,
        },
        "profile": {
            "nickname": nickname,
            "age": age,
        },
    }


# ========== 公开 API：问答 ==========

@app.get("/api/question/random")
def get_random_question(code: str, db: Session = Depends(get_db)):
    """获取一个随机待回答的问题（不返回自己提的问题）"""
    now = datetime.now(timezone.utc)

    # 查询：已审核、未过期、未被回答的问题，且不是自己提的
    query = db.query(Question).filter(
        Question.status == "approved",
        Question.asker_code != code,
    )
    # 过滤过期
    query = query.filter(
        (Question.expires_at == None) | (Question.expires_at > now)  # noqa: E711
    )
    # 只返回没有已审核回答的问题
    questions = query.all()
    available = []
    for q in questions:
        has_approved_answer = db.query(Answer).filter(
            Answer.question_id == q.id,
            Answer.status == "approved"
        ).first()
        if not has_approved_answer:
            available.append(q)

    if not available:
        return {"success": True, "question": None}

    # 随机选一个
    q = random.choice(available)
    return {
        "success": True,
        "question": {
            "id": q.id,
            "asker_nickname": q.asker_nickname,
            "asker_age": q.asker_age,
            "content": q.content,
        },
    }


@app.post("/api/answer")
def submit_answer(req: AnswerSubmitRequest, db: Session = Depends(get_db)):
    """提交回答 + 可选新问题"""
    code_str = req.code.strip().upper()
    answer_content = req.answer_content.strip()

    if not answer_content:
        return {"success": False, "error": "回答内容不能为空"}
    if len(answer_content) > 500:
        return {"success": False, "error": "回答内容不能超过500字"}

    # 基础违规词检查
    found_words = contains_sensitive(answer_content)
    if found_words:
        return {"success": False, "error": f"内容包含不适当词汇（{','.join(found_words[:3])}...），请修改后重新提交"}

    # 检查新问题
    new_question = req.new_question.strip() if req.new_question else None
    if new_question:
        if len(new_question) > 200:
            return {"success": False, "error": "问题内容不能超过200字"}
        found_q = contains_sensitive(new_question)
        if found_q:
            return {"success": False, "error": f"问题包含不适当词汇（{','.join(found_q[:3])}...），请修改后重新提交"}

    # 获取回答者档案
    profile = db.query(UserProfile).filter(UserProfile.code == code_str).first()
    if not profile:
        return {"success": False, "error": "用户信息不存在，请先兑换"}

    # 检查问题是否存在
    question = db.query(Question).filter(Question.id == req.question_id).first()
    if not question:
        return {"success": False, "error": "问题不存在"}

    # 检查是否已经回答过该问题
    existing = db.query(Answer).filter(
        Answer.question_id == req.question_id,
        Answer.answerer_code == code_str,
    ).first()
    if existing:
        return {"success": False, "error": "你已经回答过这个问题了"}

    # 创建回答
    answer = Answer(
        question_id=req.question_id,
        answerer_code=code_str,
        answerer_nickname=profile.nickname,
        answerer_age=profile.age,
        content=answer_content,
        status="pending",
    )
    db.add(answer)

    # 创建新问题（如果有）
    new_q_id = None
    if new_question:
        seven_days = timedelta(days=7)
        new_q = Question(
            asker_code=code_str,
            asker_nickname=profile.nickname,
            asker_age=profile.age,
            content=new_question,
            source="user",
            status="pending",
            created_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + seven_days,
        )
        db.add(new_q)

    db.commit()

    if new_question:
        db.refresh(new_q)
        new_q_id = new_q.id

    return {
        "success": True,
        "message": "回答已送达" + ("，您的新问题正在等待下一位有缘人" if new_question else ""),
        "answer_id": answer.id,
        "new_question_id": new_q_id,
    }


@app.post("/api/answers/query")
def query_answers(req: AnswerQueryRequest, db: Session = Depends(get_db)):
    """通过兑换码查询自己问题的回答"""
    code_str = req.code.strip().upper()

    # 查找该用户提出的所有已审核通过的问题
    questions = db.query(Question).filter(
        Question.asker_code == code_str,
    ).all()

    result = []
    for q in questions:
        # 获取该问题的已审核回答
        approved_answers = db.query(Answer).filter(
            Answer.question_id == q.id,
            Answer.status == "approved",
        ).all()

        answers_data = [
            {
                "id": a.id,
                "answerer_nickname": a.answerer_nickname,
                "answerer_age": a.answerer_age,
                "content": a.content,
                "created_at": str(a.created_at),
            }
            for a in approved_answers
        ]

        result.append({
            "question_id": q.id,
            "question_content": q.content,
            "question_status": q.status,
            "answers": answers_data,
        })

    return {
        "success": True,
        "questions": result,
    }


# ========== 管理 API：信件模板 ==========

@app.get("/api/admin/letters")
def list_letters(db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    letters = db.query(Letter).order_by(Letter.created_at.desc()).all()
    return [
        {
            "id": l.id,
            "type": l.type,
            "title": l.title,
            "content": l.content,
            "signature": l.signature,
            "created_at": str(l.created_at),
        }
        for l in letters
    ]


@app.post("/api/admin/letters")
def create_letter(data: LetterCreate, db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    letter = Letter(**data.model_dump())
    db.add(letter)
    db.commit()
    db.refresh(letter)
    return {"id": letter.id, "title": letter.title, "type": letter.type}


@app.put("/api/admin/letters/{letter_id}")
def update_letter(letter_id: int, data: LetterUpdate, db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件模板不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(letter, key, val)
    db.commit()
    return {"success": True}


@app.delete("/api/admin/letters/{letter_id}")
def delete_letter(letter_id: int, db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    letter = db.query(Letter).filter(Letter.id == letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件模板不存在")
    code_count = db.query(Code).filter(Code.letter_id == letter_id).count()
    if code_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"该信件模板关联了 {code_count} 个兑换码，请先删除相关兑换码",
        )
    db.delete(letter)
    db.commit()
    return {"success": True}


# ========== 管理 API：兑换码 ==========

@app.get("/api/admin/codes")
def list_codes(
    status: Optional[str] = Query(None),
    batch_id: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    authorized=Depends(verify_admin),
):
    query = db.query(Code)
    if status:
        query = query.filter(Code.status == status)
    if batch_id:
        query = query.filter(Code.batch_id == batch_id)

    total = query.count()
    codes = (
        query.order_by(Code.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": c.id,
                "code": c.code,
                "letter_id": c.letter_id,
                "letter_title": c.letter.title if c.letter else None,
                "status": c.status,
                "used_at": str(c.used_at) if c.used_at else None,
                "batch_id": c.batch_id,
                "created_at": str(c.created_at),
            }
            for c in codes
        ],
    }


@app.post("/api/admin/codes/generate")
def generate_codes(data: CodeGenerateRequest, db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    letter = db.query(Letter).filter(Letter.id == data.letter_id).first()
    if not letter:
        raise HTTPException(status_code=404, detail="信件模板不存在")

    batch_id = data.batch_id or datetime.now().strftime("%Y%m%d%H%M%S")
    generated = []
    for _ in range(data.quantity):
        while True:
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code_str = f"{data.prefix}-{suffix}"
            if not db.query(Code).filter(Code.code == code_str).first():
                break
        c = Code(code=code_str, letter_id=data.letter_id, batch_id=batch_id)
        db.add(c)
        generated.append(code_str)

    db.commit()
    return {"batch_id": batch_id, "quantity": len(generated), "codes": generated}


@app.delete("/api/admin/codes/{code_id}")
def delete_code(code_id: int, db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    code = db.query(Code).filter(Code.id == code_id).first()
    if not code:
        raise HTTPException(status_code=404, detail="兑换码不存在")
    if code.status == "used":
        raise HTTPException(status_code=400, detail="已使用的兑换码不能删除")
    db.delete(code)
    db.commit()
    return {"success": True}


# ========== 管理 API：统计 ==========

@app.get("/api/admin/stats")
def get_stats(db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    total_codes = db.query(Code).count()
    used_codes = db.query(Code).filter(Code.status == "used").count()
    active_codes = db.query(Code).filter(Code.status == "active").count()
    total_letters = db.query(Letter).count()

    popular = (
        db.query(Code.letter_id, func.count(Code.id).label("count"))
        .filter(Code.status == "used")
        .group_by(Code.letter_id)
        .order_by(func.count(Code.id).desc())
        .first()
    )

    popular_letter = None
    if popular:
        letter = db.query(Letter).filter(Letter.id == popular[0]).first()
        if letter:
            popular_letter = {
                "id": letter.id,
                "title": letter.title or letter.type,
                "count": popular[1],
            }

    # 问答统计
    total_questions = db.query(Question).count()
    pending_questions = db.query(Question).filter(Question.status == "pending").count()
    approved_questions = db.query(Question).filter(Question.status == "approved").count()
    answered_questions = db.query(Question).filter(Question.status == "answered").count()
    total_answers = db.query(Answer).count()
    pending_answers = db.query(Answer).filter(Answer.status == "pending").count()

    return {
        "total_codes": total_codes,
        "used_codes": used_codes,
        "active_codes": active_codes,
        "total_letters": total_letters,
        "popular_letter": popular_letter,
        "total_questions": total_questions,
        "pending_questions": pending_questions,
        "approved_questions": approved_questions,
        "answered_questions": answered_questions,
        "total_answers": total_answers,
        "pending_answers": pending_answers,
    }


# ========== 管理 API：问答审核 ==========

@app.get("/api/admin/questions")
def list_questions(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    authorized=Depends(verify_admin),
):
    query = db.query(Question)
    if status:
        query = query.filter(Question.status == status)
    if source:
        query = query.filter(Question.source == source)

    total = query.count()
    questions = (
        query.order_by(Question.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": q.id,
                "asker_code": q.asker_code,
                "asker_nickname": q.asker_nickname,
                "asker_age": q.asker_age,
                "content": q.content,
                "source": q.source,
                "status": q.status,
                "created_at": str(q.created_at),
                "expires_at": str(q.expires_at) if q.expires_at else None,
            }
            for q in questions
        ],
    }


@app.put("/api/admin/questions/{question_id}/review")
def review_question(question_id: int, req: ReviewRequest, db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="问题不存在")

    if req.action == "approve":
        question.status = "approved"
        if not question.expires_at:
            question.expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    elif req.action == "reject":
        question.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="操作无效，请使用 approve 或 reject")

    db.commit()
    return {"success": True, "status": question.status}


@app.get("/api/admin/answers")
def list_answers(
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    authorized=Depends(verify_admin),
):
    query = db.query(Answer)
    if status:
        query = query.filter(Answer.status == status)

    total = query.count()
    answers = (
        query.order_by(Answer.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": a.id,
                "question_id": a.question_id,
                "question_content": a.question.content if a.question else None,
                "answerer_code": a.answerer_code,
                "answerer_nickname": a.answerer_nickname,
                "answerer_age": a.answerer_age,
                "content": a.content,
                "status": a.status,
                "created_at": str(a.created_at),
            }
            for a in answers
        ],
    }


@app.put("/api/admin/answers/{answer_id}/review")
def review_answer(answer_id: int, req: ReviewRequest, db: Session = Depends(get_db), authorized=Depends(verify_admin)):
    answer = db.query(Answer).filter(Answer.id == answer_id).first()
    if not answer:
        raise HTTPException(status_code=404, detail="回答不存在")

    if req.action == "approve":
        answer.status = "approved"
        # 将对应问题标记为已回答
        question = db.query(Question).filter(Question.id == answer.question_id).first()
        if question:
            question.status = "answered"
    elif req.action == "reject":
        answer.status = "rejected"
    else:
        raise HTTPException(status_code=400, detail="操作无效，请使用 approve 或 reject")

    db.commit()
    return {"success": True, "status": answer.status}


# ========== 静态文件 ==========

static_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    print("Jieyou Xinxiang API starting...")
    print("   Frontend: http://localhost:8000")
    print("   Admin:    http://localhost:8000/jieyou.html")
    print("   API docs: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000)
