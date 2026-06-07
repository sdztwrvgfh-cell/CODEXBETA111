# Sistema de autenticação de usuários do Codex.AI
# Usa SQLite (built-in Python) + hashlib para hash de senhas

import sqlite3
import hashlib
import os
import json
from datetime import datetime

DB_PATH = "codex_users.db"


def _get_connection():
    """Retorna conexão com o banco SQLite"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Cria as tabelas se não existirem"""
    conn = _get_connection()
    cursor = conn.cursor()

    # Tabela de usuários
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name TEXT,
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            last_login TEXT
        )
    """)

    # Tabela de histórico de conversas por usuário
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            role TEXT NOT NULL,       -- 'user' ou 'assistant'
            content TEXT NOT NULL,
            type TEXT DEFAULT 'text', -- 'text' ou 'image'
            created_at TEXT DEFAULT (datetime('now', 'localtime')),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Índice para buscas rápidas
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chat_user 
        ON chat_history(user_id, created_at)
    """)

    conn.commit()
    conn.close()


def _hash_password(password: str) -> str:
    """Gera hash seguro da senha usando PBKDF2-SHA256"""
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Armazena salt + key juntos em hex
    return salt.hex() + ":" + key.hex()


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verifica se a senha confere com o hash armazenado"""
    try:
        salt_hex, key_hex = stored_hash.split(":")
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
        new_key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return new_key == stored_key
    except Exception:
        return False


def register_user(username: str, password: str, display_name: str = None) -> tuple:
    """
    Registra um novo usuário.
    Retorna (success: bool, message: str, user_id: int or None)
    """
    if not username or len(username.strip()) < 3:
        return False, "Nome de usuário deve ter pelo menos 3 caracteres.", None
    if not password or len(password) < 4:
        return False, "Senha deve ter pelo menos 4 caracteres.", None

    username = username.strip().lower()
    display_name = display_name.strip() if display_name else username

    conn = _get_connection()
    try:
        cursor = conn.cursor()

        # Verifica se usuário já existe
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, f"Usuário '{username}' já existe. Escolha outro nome.", None

        password_hash = _hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, display_name) VALUES (?, ?, ?)",
            (username, password_hash, display_name)
        )
        conn.commit()
        user_id = cursor.lastrowid
        return True, f"Conta criada com sucesso! Bem-vindo(a), {display_name}! 🎉", user_id
    except Exception as e:
        return False, f"Erro ao criar conta: {e}", None
    finally:
        conn.close()


def login_user(username: str, password: str) -> tuple:
    """
    Autentica um usuário.
    Retorna (success: bool, message: str, user_data: dict or None)
    """
    if not username or not password:
        return False, "Preencha usuário e senha.", None

    username = username.strip().lower()

    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password_hash, display_name, created_at FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()

        if not row:
            return False, "Usuário não encontrado.", None

        if not _verify_password(password, row["password_hash"]):
            return False, "Senha incorreta.", None

        # Atualiza último login
        cursor.execute(
            "UPDATE users SET last_login = datetime('now', 'localtime') WHERE id = ?",
            (row["id"],)
        )
        conn.commit()

        user_data = {
            "id": row["id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "created_at": row["created_at"]
        }
        return True, f"Bem-vindo(a) de volta, {row['display_name']}! 🚀", user_data
    except Exception as e:
        return False, f"Erro ao fazer login: {e}", None
    finally:
        conn.close()


def get_user_chat_history(user_id: int) -> list:
    """Carrega o histórico de chat de um usuário específico"""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT role, content, type, created_at FROM chat_history WHERE user_id = ? ORDER BY id ASC",
            (user_id,)
        )
        rows = cursor.fetchall()
        return [
            {"role": row["role"], "content": row["content"], "type": row["type"]}
            for row in rows
        ]
    except Exception:
        return []
    finally:
        conn.close()


def save_chat_message(user_id: int, role: str, content: str, msg_type: str = "text"):
    """Salva uma mensagem no histórico do usuário"""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO chat_history (user_id, role, content, type) VALUES (?, ?, ?, ?)",
            (user_id, role, content, msg_type)
        )
        conn.commit()
    except Exception:
        pass  # Não quebra o app se falhar ao salvar
    finally:
        conn.close()


def clear_user_chat_history(user_id: int):
    """Limpa todo o histórico de chat de um usuário"""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))
        conn.commit()
    except Exception:
        pass
    finally:
        conn.close()


def get_all_users() -> list:
    """Lista todos os usuários (para debug/admin)"""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, display_name, created_at, last_login FROM users ORDER BY username")
        return [dict(row) for row in cursor.fetchall()]
    except Exception:
        return []
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    """Remove um usuário e todo seu histórico"""
    conn = _get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return True
    except Exception:
        return False
    finally:
        conn.close()


# Inicializa o banco ao importar o módulo
init_db()