from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column
from src.core.databases.base_model import BaseModel

class Token(BaseModel):
    __tablename__ = "tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(String(128), nullable=False, unique=True, index=True)
    token_type: Mapped[str] = mapped_column(String(16), nullable=False)  # access/refresh
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    token: Mapped[str] = mapped_column(Text, nullable=False)
    revoked: Mapped[bool] = mapped_column(default=False, nullable=False)

    def __repr__(self) -> str:
        return f"<Token id={self.id} user_id={self.user_id} jti={self.jti} type={self.token_type} revoked={self.revoked}>"
