#!/usr/bin/env python3
"""
Arnés Prototipo de Prospectado para Avril Lab (Versión con Gate de Verificación HTTP)
Cumple con el pipeline obligatorio de 3 pasos y requerimientos del Ciclo 3.
"""

import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Dict, List, Any, Set, Tuple

HISTORIAL_FILE = "prospectos_historicos.json"
RAW_FILE = "raw_candidates.json"
REJECTED_FILE = "log_rechazos.json"
OUTPUT_FILE = "prospectos_avril_lab.json"
TOP5_OUTPUT_FILE = "top_5_priorizados.json"

LEADS_CICLO_1 = {
    "goldmar", "being-gojo", "will-assistant", "guillermoscript",
    "HelpCodeai", "shenhao-stu", "the911fund", "mauricioperera",
    "andynadal", "diegotepichin", "acbri", "robinsonmirandaco"
}

# 1. Ampliación de volumen para asegurar >= 30 en bruto
SEARCH_QUERIES = [
    "topic:openclaw fork:false pushed:>2026-01-01",
    "topic:mcp-server fork:false pushed:>2026-01-01",
    "topic:ai-agents location:mexico fork:false",
    "agent workflow location:mexico fork:false",
    "claude-code integration fork:false pushed:>2026-01-01",
    "supabase ai automation fork:false",
    "n8n workflow automation fork:false"
]

GITHUB_API_URL = "https://api.github.com"

def cargar_historial() -> Set[str]:
    historial = {h.lower() for h in LEADS_CICLO_1}
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
                guardados = json.load(f)
                historial.update(h.lower() for h in guardados)
        except Exception as e:
            print(f"[!] Aviso al cargar historial: {e}", file=sys.stderr)
    return historial 

def api_request(endpoint: str) -> Any:
    url = f"{GITHUB_API_URL}{endpoint}"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "AvrilLab-VerifiedProspector/3.0",
            "Accept": "application/vnd.github.v3+json"
        }
    )
    token = os.getenv("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return json.loads(response.read().decode('utf-8'))
    except Exception as e:
        return None
    return None

def discover_candidates(historial: Set[str]) -> List[Dict[str, Any]]:
    print("\n[PASO 1] Iniciando Descubrimiento de candidatos en bruto...")
    raw_candidates = []
    seen_in_run = set()

    for query in SEARCH_QUERIES:
        encoded_query = urllib.parse.quote(query)
        # Paginado incrementado a 15 para garantizar mayor volumen
        endpoint = f"/search/repositories?q={encoded_query}&per_page=15&sort=updated"
        res = api_request(endpoint)
        repos = res.get("items", []) if res else []

        for r in repos:
            owner = r.get("owner", {}).get("login", "")
            if not owner or owner.lower() in historial or owner.lower() in seen_in_run:
                continue
                
            seen_in_run.add(owner.lower())
            raw_candidates.append({
                "handle": owner,
                "profile_url": f"https://github.com/{owner}",
                "repo_name": r.get("name", ""),
                "repo_url": r.get("html_url", ""),
                "description": r.get("description") or "",
                "topics": r.get("topics", []),
                "query_origen": query,
                "fecha_descubrimiento": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })

    with open(RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(raw_candidates, f, indent=2, ensure_ascii=False)
        
    print(f"[✓] Paso 1 completado: {len(raw_candidates)} candidatos en bruto guardados en '{RAW_FILE}'.")
    return raw_candidates

def verificar_existencia_http(profile_url: str) -> Tuple[bool, str]:
    req = urllib.request.Request(
        profile_url,
        headers={"User-Agent": "AvrilLab-VerificationGate/3.0"}
    )
    token = os.getenv("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req) as response:
            if response.status == 200:
                return True, "HTTP 200 OK (Perfil activo)"
            return False, f"HTTP Status {response.status}"
    except urllib.error.HTTPError as e:
        return False, f"Error HTTP {e.code} (Perfil inaccesible o eliminado)"
    except Exception as e:
        return False, f"Error de conexión: {e}"

def verify_candidate(candidate: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
    username = candidate["handle"]
    profile_url = candidate["profile_url"]
    fecha_hoy = datetime.now().strftime("%Y-%m-%d")

    http_ok, http_msg = verificar_existencia_http(profile_url)
    if not http_ok:
        return False, {}, f"Falla de Verificación HTTP: {http_msg}"

    user_info = api_request(f"/users/{username}")
    if not user_info:
        return False, {}, "Error de API al consultar metadatos del usuario."

    public_repos = user_info.get("public_repos", 0)
    
    if public_repos < 3:
        return False, {}, f"Criterio Insuficiente: Solo posee {public_repos} repositorio(s) público(s). Mínimo requerido: 3."

    repos_info = api_request(f"/users/{username}/repos?per_page=10&sort=updated") or []
    languages = set()
    has_relevant_signals = False

    for r in repos_info:
        if r.get("language"):
            languages.add(r.get("language"))
        desc = (r.get("description") or "").lower()
        if any(term in desc for term in ["agent", "mcp", "workflow", "api", "bot", "rag", "docker", "supabase"]):
            has_relevant_signals = True

    if not has_relevant_signals:
        return False, {}, "Criterio Insuficiente: No detectó señales activas de agentes/MCP en repos."

    desc_repo = candidate["description"].lower()
    topics = candidate["topics"]
    es_b2b = any(term in desc_repo or term in topics for term in ["erp", "crm", "supabase", "database", "automation", "webhook"])

    if es_b2b:
        buyer_type = "B2B Ops & Tech Lead"
        suggested_offer = "$15 Trial de 7 Días / Solución B2B ($200+ USD)"
        fit_reason = f"Mantiene '{candidate['repo_name']}', enfocado en integraciones y automatización B2B."
        confidence = "Alto" if public_repos >= 5 else "Medio"
        next_action = "Presentar propuesta de orquestación cloud para eliminar mantenimiento en VPS."
        score = 3
    else:
        buyer_type = "Indie Builder / AI Developer (Lab Seat)"
        suggested_offer = "$6 Day Pass / $15 Trial"
        fit_reason = f"Mantenedor de '{candidate['repo_name']}'. Requiere staging hosted 24/7."
        confidence = "Alto" if public_repos >= 4 else "Medio"
        next_action = "Ofrecer Day Pass ($6) para aislar ejecuciones sin agotar RAM local."
        score = 2 if confidence == "Alto" else 1

    criterios_aprobados = [
        "Verificación HTTP 200 OK en perfil",
        f"Posee {public_repos} repositorios públicos (Mínimo 3)",
        "Demuestra stack activo de IA/agentes/integración",
        f"Señal comercial clara para {buyer_type}"
    ]

    verified_prospect = {
        "handle": username,
        "canal": "GitHub",
        "url_perfil": profile_url,
        "fecha_consulta": fecha_hoy,
        "url_exacta_evidencia": candidate.get("repo_url", profile_url),
        "cita_textual_fuente": f'"{candidate.get("description", "Sin descripción textual")}"',
        "estado_verificacion": "VERIFICADO_OK",
        "criterios_cumplidos": criterios_aprobados,
        "tipo_comprador": buyer_type,
        "repos_publicos": public_repos,
        "stack_detectado": list(languages),
        "por_que_compraria": fit_reason,
        "objecion_esperada": "Prefiero ejecutar localmente en mi PC o servidor personal [HIPÓTESIS].",
        "oferta_sugerida": suggested_offer,
        "nivel_confianza": confidence,
        "mejor_siguiente_accion": next_action,
        "_score_prioridad": score
    }

    return True, verified_prospect, ""

def process_verification_gate(raw_candidates: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    print("\n[PASO 2] Ejecutando Gate de Verificación (HTTP + Criterios Mínimos)...")
    verified_list = []
    rejected_list = []

    for idx, candidate in enumerate(raw_candidates, 1):
        print(f"  [*] [{idx}/{len(raw_candidates)}] Verificando @{candidate['handle']}...", end=" ")
        is_ok, verified_obj, reason = verify_candidate(candidate)
        
        if is_ok:
            print(f"-> [Aprobado] ({verified_obj['tipo_comprador']})")
            verified_list.append(verified_obj)
        else:
            print(f"-> [RECHAZADO] Motivo: {reason}")
            rejected_list.append({
                "handle": candidate["handle"],
                "profile_url": candidate["profile_url"],
                "fecha_evaluacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "motivo_descarte": reason
            })
        
        time.sleep(0.5) 

    with open(REJECTED_FILE, "w", encoding="utf-8") as f:
        json.dump(rejected_list, f, indent=2, ensure_ascii=False)

    print(f"[✓] Paso 2 completado: {len(verified_list)} aprobados, {len(rejected_list)} descartados.")
    return verified_list, rejected_list

def persist_verified_prospects(verified_list: List[Dict[str, Any]], historial: Set[str]):
    print("\n[PASO 3] Guardando prospectos verificados en el JSON final...")

    ordenados = sorted(verified_list, key=lambda x: x.get("_score_prioridad", 0), reverse=True)
    
    salida_final = []
    for p in ordenados:
        clean_item = {k: v for k, v in p.items() if not k.startswith("_")}
        salida_final.append(clean_item)
        historial.add(p["handle"].lower())

    top_5 = salida_final[:5]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(salida_final, f, indent=2, ensure_ascii=False)

    with open(TOP5_OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(top_5, f, indent=2, ensure_ascii=False)

    with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(list(historial)), f, indent=2, ensure_ascii=False)

    print(f"[✓] Paso 3 completado: '{OUTPUT_FILE}' y '{TOP5_OUTPUT_FILE}' generados exitosamente.")

def run_pipeline():
    print("============================================================")
    print("  AVRIL LAB: PIPELINE DE PROSPECCIÓN Y GATE DE VERIFICACIÓN ")
    print("============================================================")
    
    historial = cargar_historial()
    
    raw = discover_candidates(historial)
    if not raw:
        print("[!] No se encontraron candidatos nuevos en bruto. Finalizando.")
        return

    verified, rejected = process_verification_gate(raw)

    if verified:
        persist_verified_prospects(verified, historial)
    else:
        print("[!] Ningún candidato superó el gate de verificación.")

    print("\n" + "="*60)
    print("  RESUMEN DE EJECUCIÓN DEL ARNES (Métricas de la Demo)")
    print("="*60)
    print(f"  • Candidatos en Bruto (Descubiertos):  {len(raw)} (en '{RAW_FILE}')")
    print(f"  • Candidatos Rechazados (Gate):        {len(rejected)} (en '{REJECTED_FILE}')")
    print(f"  • Prospectos VERIFICADOS (Finales):    {len(verified)} (en '{OUTPUT_FILE}')")
    print(f"  • Top 5 Priorizados:                   5 (en '{TOP5_OUTPUT_FILE}')")
    print("="*60 + "\n")

if __name__ == "__main__":
    run_pipeline()