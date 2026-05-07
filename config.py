import os
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv(r"E:\RED\.env")


@dataclass
class AppConfig:
    llm_base_url: str
    llm_model: str
    obsidian_url: str
    obsidian_api_key: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_pass: str
    ftp_host: str
    ftp_user: str
    ftp_pass: str
    prototype_base_url: str
    tracking_port: int
    ngrok_enabled: bool

    MUNICIPALITIES: list = field(default_factory=lambda: [
        "Moncada",
        "Alfara del Patriarca",
        "Burjassot",
        "Godella",
        "Masarrojos"
    ])

    CATEGORIES: dict = field(default_factory=lambda: {
        "restaurante-bar":       ["restaurante", "bar", "tapas"],
        "horchateria-cafeteria": ["horchateria", "cafeteria"],
        "peluqueria-barberia":   ["peluqueria", "barberia"],
        "taller-mecanico":       ["taller", "mecanico", "garaje"],
        "tienda-alimentacion":   ["tienda", "fruteria", "carniceria"],
        "clinica-fisio":         ["clinica", "fisioterapia", "estetica"],
        "academia":              ["academia", "autoescuela", "clases"],
        "reformas-servicios":    ["reformas", "fontanero", "electricista"]
    })


Config = AppConfig(
    llm_base_url=os.getenv("LLM_BASE_URL", "http://localhost:1234/v1"),
    llm_model=os.getenv("LLM_MODEL", "gemma-4-26b"),
    obsidian_url=os.getenv("OBSIDIAN_URL", "http://127.0.0.1:27123"),
    obsidian_api_key=os.getenv("OBSIDIAN_API_KEY", ""),
    smtp_host=os.getenv("SMTP_HOST", "pending"),
    smtp_port=int(os.getenv("SMTP_PORT", "587")),
    smtp_user=os.getenv("SMTP_USER", "pending"),
    smtp_pass=os.getenv("SMTP_PASS", "pending"),
    ftp_host=os.getenv("FTP_HOST", "pending"),
    ftp_user=os.getenv("FTP_USER", "pending"),
    ftp_pass=os.getenv("FTP_PASS", "pending"),
    prototype_base_url=os.getenv("PROTOTYPE_BASE_URL", "https://prototipos.rbninformatica.com"),
    tracking_port=int(os.getenv("TRACKING_PORT", "8765")),
    ngrok_enabled=os.getenv("NGROK_ENABLED", "false").lower() == "true",
)