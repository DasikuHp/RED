import sys
sys.path.insert(0, r"E:\RED")
from openai import OpenAI
from config import Config

def generate_email(lead: dict, variant: str, demo_url: str) -> dict:
    if lead["language"] == "val":
        instruction = "Escriu en valencia (catala valencian)."
    else:
        instruction = "Escribe en español."

    if variant == "A":
        prompt = (
            f"{instruction} "
            f"Escribe un email comercial breve de maximo 100 palabras "
            f"para {lead['business_name']}, "
            f"un {lead['category']} en {lead['municipality']}. "
            f"Hemos creado un prototipo de su web: {demo_url} "
            f"El email debe mencionar que vimos que no tienen web, "
            f"mostrar el enlace prominentemente, "
            f"ofrecer mantenimiento mensual con RBN Informatica. "
            f"Asunto: incluyelo como primera linea con el formato: "
            f"ASUNTO: [texto del asunto] "
            f"Firma: RBN Informatica"
        )
    else: # Default to VARIANT B
        prompt = (
            f"{instruction} "
            f"Escribe un email comercial breve de maximo 100 palabras "
            f"para {lead['business_name']}, "
            f"un {lead['category']} en {lead['municipality']}. "
            f"Empieza mencionando lo que pierden sin web "
            f"(clientes que buscan online y no los encuentran). "
            f"Despues presenta la solucion: hemos creado su prototipo: {demo_url} "
            f"Asunto: incluyelo como primera linea con el formato: "
            f"ASUNTO: [texto del asunto] "
            f"Firma: RBN Informatica"
        )

    client = OpenAI(
        base_url=Config.LLM_BASE_URL,
        api_key="not-needed"
    )
    
    response = client.chat.completions.create(
        model=Config.LLM_MODEL,
        messages=[{"role": "user", "content": prompt}]
    )
    content = response.choices[0].message.content.strip()

    lines = content.split("\n")
    subject = ""
    body_lines = []
    for line in lines:
        # Clean the line to check for ASUNTO variations (e.g. **ASUNTO:**, ASUNTO :, etc)
        test_line = line.strip().upper().replace("*", "").replace(" ", "")
        if test_line.startswith("ASUNTO:"):
            if ":" in line:
                subject = line.split(":", 1)[1].strip().replace("**", "")
        else:
            body_lines.append(line)
            
    body = "\n".join(body_lines).strip()

    return {"subject": subject, "body": body, "variant": variant}
