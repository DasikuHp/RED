import sys
import os
sys.path.insert(0, r"E:\RED")

import typer
import sqlite3
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich import box
from loguru import logger

app = typer.Typer(
    help="RED — Sistema de captacion RBN Informatica",
    add_completion=False
)
console = Console()
DB_PATH = r"E:\RED\red.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# ── SETUP ────────────────────────────────────────
@app.command()
def setup():
    """Inicializa vault Obsidian, DB y verifica conexiones."""
    console.print(Panel(
        "[bold cyan]RED Setup[/bold cyan]",
        subtitle="Inicializando sistema"
    ))
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        t1 = progress.add_task("Inicializando SQLite...", total=None)
        try:
            import db
            db.init_db() if hasattr(db, "init_db") else None
            progress.update(t1, description="[green]SQLite OK[/green]")
        except Exception as e:
            progress.update(t1, description=f"[red]SQLite: {e}[/red]")
        
        t2 = progress.add_task("Conectando Obsidian...", total=None)
        try:
            from obsidian_bridge import setup_vault
            setup_vault()
            progress.update(t2, description="[green]Obsidian vault OK[/green]")
        except Exception as e:
            progress.update(t2, description=f"[yellow]Obsidian: {e}[/yellow]")
        
        t3 = progress.add_task("Verificando LM Studio...", total=None)
        try:
            import httpx
            r = httpx.get("http://localhost:1234/v1/models", timeout=3)
            progress.update(t3, description=f"[green]LM Studio OK[/green]")
        except Exception:
            progress.update(t3, description="[yellow]LM Studio: offline (normal)[/yellow]")
    
    console.print("[green]Setup completado.[/green]")

# ── STATUS ───────────────────────────────────────
@app.command()
def status():
    """Dashboard del sistema con metricas en tiempo real."""
    console.print(Panel(
        "[bold cyan]RED — Estado del Sistema[/bold cyan]",
        subtitle=datetime.now().strftime("%Y-%m-%d %H:%M")
    ))
    try:
        conn = get_conn()
        c = conn.cursor()
        
        # Tabla leads por estado
        t = Table(
            title="Leads por Estado",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold magenta"
        )
        t.add_column("Estado", style="cyan")
        t.add_column("Total", justify="right")
        t.add_column("Barra", width=20)
        
        c.execute("""
            SELECT status, COUNT(*) as n
            FROM leads
            GROUP BY status
            ORDER BY n DESC
        """)
        rows = c.fetchall()
        total_leads = sum(r["n"] for r in rows) if rows else 0
        
        STATUS_COLORS = {
            "sin_verificar": "yellow",
            "verificado": "green",
            "contactado": "blue",
            "respondio": "bright_green",
            "convertido": "bold green",
            "descartado": "red",
            "frio": "dim"
        }
        for row in rows:
            pct = int((row["n"] / total_leads * 20)) if total_leads else 0
            bar = "[" + "█" * pct + "░" * (20-pct) + "]"
            color = STATUS_COLORS.get(row["status"], "white")
            t.add_row(
                f"[{color}]{row['status']}[/{color}]",
                str(row["n"]),
                f"[{color}]{bar}[/{color}]"
            )
        console.print(t)
        
        # Tabla campañas
        c.execute("""
            SELECT COUNT(*) as total,
                   SUM(opened) as opens,
                   SUM(clicked) as clicks,
                   SUM(replied) as replies
            FROM campaigns
        """)
        camp = c.fetchone()
        if camp and camp["total"]:
            t2 = Table(
                title="Campanas Email",
                box=box.ROUNDED,
                header_style="bold blue"
            )
            t2.add_column("Metrica")
            t2.add_column("Valor", justify="right")
            t2.add_column("Tasa", justify="right")
            total_c = camp["total"] or 1
            t2.add_row("Enviados", str(camp["total"]), "100%")
            t2.add_row(
                "Abiertos",
                str(camp["opens"] or 0),
                f"{(camp['opens'] or 0)/total_c:.0%}"
            )
            t2.add_row(
                "Clicks",
                str(camp["clicks"] or 0),
                f"{(camp['clicks'] or 0)/total_c:.0%}"
            )
            t2.add_row(
                "[green]Respuestas[/green]",
                f"[green]{camp['replies'] or 0}[/green]",
                f"[green]{(camp['replies'] or 0)/total_c:.0%}[/green]"
            )
            console.print(t2)
        
        # Top leads
        c.execute("""
            SELECT business_name, category,
                   municipality, score, tier
            FROM leads
            WHERE score IS NOT NULL AND score > 0
            ORDER BY score DESC LIMIT 5
        """)
        top = c.fetchall()
        if top:
            t3 = Table(
                title="Top 5 Leads por Score",
                box=box.SIMPLE,
                header_style="bold yellow"
            )
            t3.add_column("Negocio", style="cyan")
            t3.add_column("Categoria")
            t3.add_column("Municipio")
            t3.add_column("Score", justify="right")
            t3.add_column("Tier", justify="center")
            TIER_COLORS = {"A":"green","B":"yellow","C":"red","D":"dim"}
            for row in top:
                tc = TIER_COLORS.get(row["tier"], "white")
                t3.add_row(
                    row["business_name"],
                    row["category"],
                    row["municipality"],
                    str(row["score"]),
                    f"[{tc}]{row['tier']}[/{tc}]"
                )
            console.print(t3)
        
        # SEAL última ejecución
        c.execute("""
            SELECT run_date, COUNT(*) as n
            FROM seal_insights
            GROUP BY run_date
            ORDER BY run_date DESC LIMIT 1
        """)
        seal = c.fetchone()
        if seal:
            console.print(f"\n[dim]Ultimo SEAL: {seal['run_date']} " 
                         f"({seal['n']} sugerencias)[/dim]")
        conn.close()
    
    except Exception as e:
        console.print(f"[red]Error en status: {e}[/red]")

# ── DISCOVER ─────────────────────────────────────
@app.command()
def discover(
    zona: str = typer.Option(..., "--zona", "-z",
                              help="Municipio a scrapear"),
    cat:  str = typer.Option(..., "--cat", "-c",
                              help="Categoria de negocio"),
    max_results: int = typer.Option(30, "--max", "-m")
):
    """Scraping Maps + verificacion + extraccion contacto."""
    console.print(Panel(
        f"[cyan]Discover: {cat} en {zona}[/cyan] "
        f"(max {max_results})"
    ))
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        t1 = progress.add_task(
            f"Scraping Maps: {cat} {zona}...", total=None
        )
        try:
            sys.path.insert(0, r"E:\RED\01_discovery")
            from maps_scraper import scrape_maps
            leads = scrape_maps(zona, cat, max_results)
            progress.update(t1,
                description=f"[green]Scraping OK: {len(leads)} leads[/green]"
            )
        except Exception as e:
            progress.update(t1,
                description=f"[red]Scraping error: {e}[/red]"
            )
            return
        
        t2 = progress.add_task("Verificando webs...", total=None)
        try:
            from web_verifier import verify_all_pending
            results = verify_all_pending()
            progress.update(t2,
                description=f"[green]Verificados: {results}[/green]"
            )
        except Exception as e:
            progress.update(t2,
                description=f"[yellow]Verifier: {e}[/yellow]"
            )
    
    console.print(f"[green]Discover completado.[/green] " 
                  f"Ejecuta [cyan]red score[/cyan] para puntuar.")

# ── SCORE ────────────────────────────────────────
@app.command()
def score():
    """Puntua todos los leads verificados sin score."""
    console.print(Panel("[cyan]Scoring de leads[/cyan]"))
    try:
        sys.path.insert(0, r"E:\RED\02_scoring")
        from lead_scorer import score_all_verified
        with console.status("Calculando scores..."):
            results = score_all_verified()
        console.print(f"[green]Scored: {len(results)} leads[/green]")
        if results:
            t = Table(box=box.SIMPLE, header_style="bold")
            t.add_column("ID")
            t.add_column("Score", justify="right")
            t.add_column("Tier")
            for lead_id, s in results[:10]:
                tier = ("A" if s>=75 else "B" if s>=50
                        else "C" if s>=25 else "D")
                color = {"A":"green","B":"yellow",
                         "C":"red","D":"dim"}[tier]
                t.add_row(str(lead_id), str(s),
                          f"[{color}]{tier}[/{color}]")
            console.print(t)
    except Exception as e:
        console.print(f"[red]Score error: {e}[/red]")

# ── GENERATE ─────────────────────────────────────
@app.command()
def generate(
    limit: int = typer.Option(3, "--limit", "-l"),
    lead_id: int = typer.Option(None, "--lead-id")
):
    """Genera prototipos HTML para los mejores leads."""
    console.print(Panel(
        f"[cyan]Generando prototipos[/cyan] (max {limit})"
    ))
    try:
        sys.path.insert(0, r"E:\RED\03_prototype")
        from prototype_gen import generate_prototype
        conn = get_conn()
        c = conn.cursor()
        if lead_id:
            ids = [lead_id]
        else:
            c.execute("""
                SELECT id FROM leads
                WHERE status='verificado'
                AND score >= 40
                ORDER BY score DESC LIMIT ?
            """, (limit,))
            ids = [r["id"] for r in c.fetchall()]
        conn.close()
        if not ids:
            console.print("[yellow]No hay leads con score >= 40[/yellow]")
            return
        with Progress(
            SpinnerColumn(),
            TextColumn("{task.description}"),
            BarColumn(),
            console=console
        ) as progress:
            task = progress.add_task(
                "Generando...", total=len(ids)
            )
            for lid in ids:
                try:
                    path = generate_prototype(lid)
                    progress.advance(task)
                    console.print(
                        f"  [green]OK[/green] Lead {lid}: {path}"
                    )
                except Exception as e:
                    progress.advance(task)
                    console.print(
                        f"  [red]FAIL[/red] Lead {lid}: {e}"
                    )
    except Exception as e:
        console.print(f"[red]Generate error: {e}[/red]")

# ── OUTREACH ─────────────────────────────────────
@app.command()
def outreach(
    limit: int = typer.Option(5, "--limit", "-l"),
    lead_id: int = typer.Option(None, "--lead-id")
):
    """Envia emails + programa seguimiento automatico."""
    console.print(Panel(
        f"[cyan]Outreach[/cyan] (max {limit})"
    ))
    console.print("[yellow]SMTP pendiente — " 
                  "configura credenciales de Ruben[/yellow]")

# ── SEAL ─────────────────────────────────────────
@app.command()
def seal():
    """Ejecuta ciclo SEAL de analisis y mejora."""
    console.print(Panel("[cyan]SEAL Engine[/cyan]"))
    try:
        sys.path.insert(0, r"E:\RED\06_seal")
        from seal_engine import run_seal_cycle
        with console.status("Analizando campanas..."):
            result = run_seal_cycle()
        t = Table(box=box.SIMPLE)
        t.add_column("Metrica")
        t.add_column("Valor", justify="right")
        t.add_row("Campanas analizadas",
                  str(result["analyzed_campaigns"]))
        t.add_row("Bajo rendimiento",
                  str(result["low_performers"]))
        t.add_row("Sugerencias generadas",
                  str(result["suggestions_generated"]))
        t.add_row("Reporte", result["report_path"])
        console.print(t)
    except Exception as e:
        console.print(f"[red]SEAL error: {e}[/red]")

# ── PIPELINE ─────────────────────────────────────
@app.command()
def pipeline(
    zona: str = typer.Option(..., "--zona", "-z"),
    cat:  str = typer.Option(..., "--cat", "-c"),
    max_results: int = typer.Option(20, "--max", "-m")
):
    """Pipeline completo: discover -> score -> generate."""
    console.print(Panel(
        f"[bold cyan]PIPELINE COMPLETO[/bold cyan]\n"
        f"Zona: {zona} | Cat: {cat} | Max: {max_results}"
    ))
    discover(zona=zona, cat=cat, max_results=max_results)
    score()
    generate(limit=3, lead_id=None)
    console.print(Panel(
        "[green]Pipeline completado.[/green]\n"
        "Siguiente: [cyan]red outreach[/cyan] "
        "(cuando tengas credenciales SMTP)"
    ))

if __name__ == "__main__":
    app()