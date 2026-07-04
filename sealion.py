#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import re
import platform
import subprocess
import sys
import shlex
from dataclasses import dataclass, field
from pathlib import Path
from shutil import which

try:
    import readline  # type: ignore
except ImportError:
    readline = None


APP_NAME = "SeaLion Console"
VERSION = "0.1.0"
ASCII_FILE = Path(__file__).with_name("ascii-art.txt")
TOOL_ROOT = Path(__file__).resolve().parent
INSTALL_ROOT = Path.home() / ".sealionconsole" / "tools"
USER_BIN = Path.home() / ".local" / "bin"


@dataclass
class ToolEntry:
    name: str
    path: Path
    install_file: Path
    help_file: Path


@dataclass
class ConsoleState:
    current_tool: ToolEntry | None = None
    last_search_results: list[ToolEntry] = field(default_factory=list)


def load_logo() -> str:
    if ASCII_FILE.exists():
        content = ASCII_FILE.read_text(encoding="utf-8", errors="replace").rstrip()
        if content:
            return content
    return APP_NAME


def normalize(value: str) -> str:
    return value.strip().lower()


def is_linux() -> bool:
    return platform.system().lower() == "linux"


def discover_tools() -> list[ToolEntry]:
    tools: list[ToolEntry] = []
    for path in sorted(TOOL_ROOT.iterdir(), key=lambda p: p.name.lower()):
        if not path.is_dir() or path.name.startswith(".") or path.name.startswith("__"):
            continue
        install_file = path / "install.py"
        help_file = path / "help.md"
        if not help_file.exists():
            help_file = path / "help.txt"
        if install_file.exists() and help_file.exists():
            tools.append(ToolEntry(name=path.name, path=path, install_file=install_file, help_file=help_file))
    return tools


def find_tool(name: str) -> ToolEntry | None:
    needle = normalize(name)
    for tool in discover_tools():
        if normalize(tool.name) == needle:
            return tool
    return None


def render_markdown(text: str) -> None:
    try:
        from rich.console import Console
        from rich.markdown import Markdown
        console = Console()
        console.print(Markdown(text))
    except ImportError:
        print(text)


def print_banner() -> None:
    print(load_logo())
    print(f"\n{APP_NAME} — personal tool vault\n")


def print_tool_help(tool: ToolEntry) -> None:
    text = tool.help_file.read_text(encoding="utf-8", errors="replace").rstrip()
    render_markdown(text)


def print_tool_entry(tool: ToolEntry, index: int | None = None) -> None:
    if index is None:
        print(f"  - {tool.name}")
    else:
        print(f"  [{index}] {tool.name}")


def print_help_text() -> None:
    print()
    print("Comandi disponibili:")
    print("  list               Elenca i tool disponibili")
    print("  search <query>     Cerca tool per nome o testo")
    print("  use <nome|num>     Seleziona un tool")
    print("  install [nome]     Installa il tool selezionato o specificato")
    print("  vuln <protocollo>  Mostra vulnerabilità e tool per un protocollo")
    print("  vuln list          Elenca i protocolli disponibili")
    print("  vuln *             Elenca i protocolli disponibili") 
    print("  help               Mostra questo aiuto")
    print("  back               Torna alla console principale")
    print("  exit               Esci da " + APP_NAME)


def get_install_dir(tool: ToolEntry) -> Path:
    return INSTALL_ROOT / tool.name


def load_install_module(tool: ToolEntry):
    spec = importlib.util.spec_from_file_location(f"sealionconsole_install_{tool.name}", tool.install_file)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run_install(tool: ToolEntry) -> int:
    if not is_linux():
        print(f" {tool.name} è disponibile solo su Linux.", file=sys.stderr)
        return 1

    install_dir = get_install_dir(tool)
    install_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nInstallazione di {tool.name}…")
    print(f"Destinazione: {install_dir}\n")

    try:
        mod = load_install_module(tool)
        rc = mod.install(install_dir)
    except Exception as exc:
        print(f"Errore durante l'installazione: {exc}", file=sys.stderr)
        return 1

    if rc != 0:
        return rc

    entry_point = getattr(mod, "ENTRY_POINT", None)
    if entry_point:
        publish_launcher(tool, install_dir, entry_point)

    return 0


def publish_launcher(tool: ToolEntry, install_dir: Path, entry_point_template: str) -> None:
    command = entry_point_template.format(dest=install_dir)

    USER_BIN.mkdir(parents=True, exist_ok=True)
    launcher_path = USER_BIN / tool.name
    launcher_body = (
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f'exec {command} "$@"\n'
    )
    launcher_path.write_text(launcher_body, encoding="utf-8")
    launcher_path.chmod(0o755)
    print(f"\nLauncher creato: {launcher_path}")

    if str(USER_BIN) not in (subprocess.run(["bash", "-lc", "echo $PATH"], capture_output=True, text=True).stdout or ""):
        print(f"  Assicurati che {USER_BIN} sia nel tuo PATH.")


def print_tool_context(tool: ToolEntry) -> None:
    print(f"\n--- {tool.name} ---")
    print(f"Cartella sorgente:       {tool.path}")
    print(f"Cartella installazione:  {get_install_dir(tool)}")
    print()
    print_tool_help(tool)
    print("\nDigita 'install' per installare, 'back' per tornare indietro.")


def tool_matches_query(tool: ToolEntry, query: str) -> bool:
    nq = normalize(query)
    if nq in normalize(tool.name):
        return True
    help_text = tool.help_file.read_text(encoding="utf-8", errors="replace").lower()
    if nq in help_text:
        return True
    return False


def resolve_target(target: str | None, state: ConsoleState | None) -> ToolEntry | None:
    if target is None:
        return state.current_tool if state is not None else None

    if target.isdigit():
        tools = discover_tools()
        if state is not None and state.last_search_results:
            tools = state.last_search_results
        index = int(target) - 1
        if 0 <= index < len(tools):
            return tools[index]

    return find_tool(target)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="slconsole", add_help=False)
    parser.add_argument("-h", "--help", action="store_true")
    parser.add_argument("--version", action="store_true")
    subparsers = parser.add_subparsers(dest="command")
    subparsers.add_parser("list")
    install_p = subparsers.add_parser("install")
    install_p.add_argument("target", nargs="?")
    use_p = subparsers.add_parser("use")
    use_p.add_argument("target")
    subparsers.add_parser("back")
    search_p = subparsers.add_parser("search")
    search_p.add_argument("query", nargs="+")
    vuln_p = subparsers.add_parser("vuln")
    vuln_p.add_argument("protocol", nargs="+")
    return parser


def parse_console_command(line: str) -> list[str]:
    tokens = shlex.split(line)
    if tokens and tokens[0].lower() in {"slconsole", "sealion", "sealionconsole"}:
        return tokens[1:]
    return tokens


def setup_readline() -> None:
    if readline is None:
        return
    try:
        readline.parse_and_bind("tab: complete")
        readline.parse_and_bind("set editing-mode emacs")
    except Exception:
        pass


def run_command(argv: list[str], state: ConsoleState | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 1

    if args.version:
        print(f"{APP_NAME} {VERSION}")
        return 0

    if args.help or args.command is None:
        print_help_text()
        return 0

    handlers = {
        "list": cmd_list,
        "install": cmd_install,
        "use": cmd_use,
        "back": cmd_back,
        "search": cmd_search,
        "vuln": cmd_vuln,
    }
    handler = handlers.get(args.command)
    if handler is None:
        print_help_text()
        return 1
    return handler(args, state)


def run_console() -> int:
    setup_readline()
    state = ConsoleState()
    print_banner()
    print("Digita 'help' per i comandi, 'exit' per uscire.")
    while True:
        try:
            prompt = f"\033[94mConsole({state.current_tool.name})> \033[0m" if state.current_tool else "\033[94mslconsole> \033[0m"
            line = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if not line:
            continue

        lowered = line.lower()
        if lowered in {"exit", "quit"}:
            return 0
        if lowered in {"help", "?"}:
            if state.current_tool:
                print_tool_context(state.current_tool)
            else:
                print_help_text()
            continue
        if lowered == "back":
            state.current_tool = None
            print("Tornato alla console principale.")
            continue

        argv = parse_console_command(line)
        if not argv:
            continue

        if state.current_tool is not None and argv[0] == "install" and len(argv) == 1:
            rc = run_install(state.current_tool)
            if rc != 0:
                print(f"Installazione terminata con errore (codice {rc}).")
            continue

        known_commands = {"list", "install", "use", "search", "vuln", "back", "help", "?", "--version", "-h", "--help"}
        if argv[0] not in known_commands:
            print("Comando non riconosciuto. Digita 'help' per i comandi.")
            continue

        rc = run_command(argv, state)
        if rc != 0 and rc != 1:
            print(f"Comando terminato con codice {rc}.")


def cmd_list(args: argparse.Namespace, state: ConsoleState | None = None) -> int:
    tools = discover_tools()
    if not tools:
        print("Nessun tool trovato.")
        print("Per aggiungere un tool, crea una cartella con install.py e help.md.")
        return 0
    print(f"\nTool disponibili ({len(tools)}):\n")
    for index, tool in enumerate(tools, start=1):
        print_tool_entry(tool, index)
    print()
    return 0


def cmd_search(args: argparse.Namespace, state: ConsoleState | None = None) -> int:
    query = " ".join(args.query) if isinstance(args.query, list) else args.query
    query = normalize(query)
    matches = [t for t in discover_tools() if tool_matches_query(t, query)]
    if not matches:
        print("Nessun risultato.")
        return 0
    if state is not None:
        state.last_search_results = matches
    print(f"\nRisultati per '{query}':\n")
    for index, tool in enumerate(matches, start=1):
        print_tool_entry(tool, index)
    print()
    return 0


def cmd_use(args: argparse.Namespace, state: ConsoleState | None = None) -> int:
    if state is None:
        print("Il comando 'use' è disponibile solo nella console interattiva.", file=sys.stderr)
        return 1
    tool = resolve_target(args.target, state)
    if not tool:
        print(f"Tool non trovato: {args.target}", file=sys.stderr)
        return 1
    state.current_tool = tool
    print_tool_context(tool)
    return 0


def cmd_back(args: argparse.Namespace, state: ConsoleState | None = None) -> int:
    if state is None:
        return 0
    state.current_tool = None
    print("Tornato alla console principale.")
    return 0


def cmd_install(args: argparse.Namespace, state: ConsoleState | None = None) -> int:
    target = getattr(args, "target", None)
    tool = resolve_target(target, state)
    if not tool:
        print("Nessun tool selezionato. Usa 'install <nome>' oppure prima 'use <nome>'.", file=sys.stderr)
        return 1
    return run_install(tool)


# ---------------------------------------------------------------------------
# vuln command — vulnerability cheatsheets per protocollo
# ---------------------------------------------------------------------------

VULN_CATEGORIES: dict[str, list[str]] = {
    "Trasferimento File": ["ftp", "smb", "nfs"],
    "DNS & Ricognizione": ["dns"],
    "Email": ["smtp", "imap-pop3"],
    "Monitoraggio Rete": ["snmp"],
    "Database": ["mysql", "mssql", "oracle-tns"],
    "Accesso Remoto": ["ssh", "rdp", "winrm", "wmi"],
    "Hardware & Management": ["ipmi"],
}

VULN_DB: dict[str, dict] = {
    "ftp": {
        "nome": "FTP — File Transfer Protocol",
        "porte": "21 (controllo), 20 (dati)",
        "categoria": "Trasferimento File",
        "descrizione": (
            "Protocollo per il trasferimento file che opera al livello Applicazione.\n"
            "Usa due canali separati: controllo (porta 21) e dati (porta 20).\n"
            "Trasmette TUTTO in chiaro: credenziali e file possono essere intercettati.\n"
            "\n"
            "Modalità Attiva: il server si connette al client per inviare dati (bloccata dai firewall).\n"
            "Modalità Passiva: il client si connette al server (più compatibile, usata oggi).\n"
            "\n"
            "TFTP (Trivial FTP): variante su UDP, senza autenticazione, solo get/put.\n"
            "Da non confondere con SFTP (SSH File Transfer) o FTPS (FTP over SSL)."
        ),
        "configurazione": [
            "Server principale Linux: vsFTPd (Very Secure FTP Daemon)",
            "File config: /etc/vsftpd.conf",
            "Utenti vietati: /etc/ftpusers (root, guest, ecc.)",
            "Vedere config attiva: cat /etc/vsftpd.conf | grep -v '#'",
        ],
        "vulnerabilità": [
            "Login anonimo (anonymous_enable=YES) — accesso senza credenziali",
            "Upload anonimo (anon_upload_enable=YES) — caricamento file malevoli",
            "Credenziali in chiaro — sniffabili con Wireshark/tcpdump",
            "hide_ids=NO — mostra i veri username dei file (utile per brute force SSH)",
            "ls_recurse_enable=YES — mappa l'intero server con ls -R in pochi secondi",
            "ssl_enable=NO — nessuna crittografia, tutto intercettabile",
            "Versioni obsolete di vsFTPd/ProFTPd con exploit noti (es. vsFTPd 2.3.4 backdoor)",
        ],
        "enumerazione": [
            "# === SCAN & RILEVAMENTO ===",
            "sudo nmap -sV -p21 -sC -A <IP>                     # Scan aggressivo porta 21",
            "sudo nmap --script ftp-anon -p21 <IP>               # Check accesso anonimo",
            "",
            "# === CONNESSIONE MANUALE ===",
            "ftp <IP> [porta]                                     # Connessione manuale",
            "  > anonymous / anonymous                            # Login anonimo",
            "  > status                                           # Info configurazione server",
            "  > debug                                            # Mostra pacchetti raw client→server",
            "  > trace                                            # Mostra ogni pacchetto scambiato",
            "  > ls -R                                            # Lista ricorsiva (se abilitata)",
            "  > get <file>                                       # Scarica un file",
            "  > put <file>                                       # Carica un file (se permesso)",
            "",
            "# === DOWNLOAD DI MASSA ===",
            "wget -m --no-passive ftp://anonymous:anonymous@<IP>  # Scarica tutto il server FTP",
            "",
            "# === CERTIFICATI & CRITTOGRAFIA ===",
            "openssl s_client -connect <IP>:21 -starttls ftp      # Verifica certificati SSL/TLS",
        ],
        "tool_consigliati": ["nmap", "nikto", "impacket"],
    },
    "smb": {
        "nome": "SMB — Server Message Block",
        "porte": "445 (SMB/CIFS), 137-139 (NetBIOS legacy)",
        "categoria": "Trasferimento File",
        "descrizione": (
            "Protocollo per la condivisione di file, stampanti e risorse in rete.\n"
            "Pilastro delle reti Windows. Su Linux si usa Samba (demoni: smbd + nmbd).\n"
            "\n"
            "Versioni: CIFS (NT4) → SMB 1.0 (2000) → SMB 2.0 (Vista) → SMB 3.1.1 (Win10+).\n"
            "La porta 445 è lo standard moderno; le porte 137-139 sono legacy NetBIOS.\n"
            "\n"
            "ACL (Access Control Lists) regolano chi può leggere/scrivere/eseguire.\n"
            "Le share possono mostrare una gerarchia diversa dal disco fisico del server."
        ),
        "configurazione": [
            "Config Samba (Linux): /etc/samba/smb.conf",
            "Vedere config attiva: cat /etc/samba/smb.conf | grep -v '#\\|;'",
            "Riavviare dopo modifiche: sudo systemctl restart smbd",
            "Sezioni: [global] per regole generali, [nome_share] per ogni condivisione",
        ],
        "vulnerabilità": [
            "Null Session — accesso anonimo senza credenziali (-N)",
            "guest ok = yes — condivisioni aperte a tutti senza password",
            "browseable = yes — share visibili a chiunque interroghi il server",
            "read only = no / writable = yes — scrittura permessa (upload web shell)",
            "create mask = 0777 — permessi massimi su file creati (RWX per tutti)",
            "logon script / magic script — se sovrascrivibili → RCE (Remote Code Execution)",
            "EternalBlue (MS17-010) — RCE su SMBv1 senza autenticazione (WannaCry/NotPetya)",
            "Enumerazione utenti via RPC (rpcclient, samrdump) — mappa tutti gli utenti del dominio",
        ],
        "enumerazione": [
            "# === ELENCO SHARE ===",
            "smbclient -N -L //<IP>                               # Elenca share (null session, senza password)",
            "smbclient //<IP>/<share>                              # Accedi a una share specifica",
            "  > !cat flag.txt                                    # '!' esegue comandi sul TUO PC senza uscire",
            "smbmap -H <IP>                                       # Mappa permessi READ/WRITE su ogni share",
            "smbmap -H <IP> -u 'user' -p 'pass'                   # Con credenziali specifiche",
            "",
            "# === ENUMERAZIONE RPC (rpcclient) ===",
            "rpcclient -U '' <IP>                                  # Sessione RPC anonima",
            "  > srvinfo                                          # Info server (nome, versione OS)",
            "  > enumdomains                                      # Elenca tutti i domini nella rete",
            "  > querydominfo                                     # Info dominio, server e utenti",
            "  > enumdomusers                                     # Lista utenti dominio con RID",
            "  > netshareenumall                                   # Lista tutte le share (anche nascoste)",
            "  > netsharegetinfo <share>                          # Dettagli su una share specifica",
            "  > queryuser <RID>                                  # Info su utente specifico (per RID)",
            "  > querygroup <RID>                                 # Info su gruppo specifico",
            "",
            "# === BRUTE FORCE RID (se enum bloccata) ===",
            "for i in $(seq 500 1100);do rpcclient -N -U '' <IP> -c \"queryuser 0x$(printf '%x\\n' $i)\" | grep 'User Name' && echo '';done",
            "samrdump.py <IP>                                      # Alternativa Python (Impacket)",
            "",
            "# === TOOL AUTOMATICI ===",
            "nxc smb <IP> --shares -u '' -p ''                    # NetExec: enum share anonime",
            "nxc smb <IP> -u 'admin' -p 'pass' --sam             # Dump hash SAM (con admin)",
            "nxc smb <SUBNET>/24 -u users.txt -p 'Password123!'  # Password spraying su subnet",
            "nxc smb <IP> -u 'admin' -p 'pass' -x 'whoami'       # Esecuzione comandi remoti",
            "enum4linux-ng.py <IP> -A                             # Enumerazione completa (porte, utenti, gruppi, share, policy password)",
            "sudo nmap -sV -sC -p139,445 <IP>                    # Nmap SMB scan",
            "",
            "# === MONITORAGGIO (lato admin) ===",
            "smbstatus                                             # Chi è connesso, versione protocollo, file lockati",
        ],
        "tool_consigliati": ["nmap", "enum4linux-ng", "smbmap", "crackmapexec", "impacket"],
    },
    "nfs": {
        "nome": "NFS — Network File System",
        "porte": "2049 (NFS), 111 (RPCBind/Portmapper)",
        "categoria": "Trasferimento File",
        "descrizione": (
            "Protocollo per accedere a filesystem remoti come se fossero locali.\n"
            "Usato principalmente su Linux/Unix. Non può comunicare con SMB.\n"
            "\n"
            "Non ha meccanismi di autenticazione propri — si fida del UID/GID del client.\n"
            "NFSv4 usa porta unica 2049 TCP/UDP. Versioni precedenti necessitano anche di RPCBind (porta 111).\n"
            "\n"
            "Versioni: NFSv2 (UDP) → NFSv3 (file variabili) → NFSv4 (Kerberos, ACL, stateful) → NFSv4.1 (pNFS parallelo).\n"
            "Usa ONC-RPC e formato XDR per compatibilità tra SO diversi."
        ),
        "configurazione": [
            "File export: /etc/exports (tabella filesystem condivisi)",
            "Vedere config: cat /etc/exports",
            "Riavviare dopo modifiche: exportfs -ra",
            "Opzioni chiave: rw/ro, sync/async, secure/insecure, root_squash/no_root_squash",
        ],
        "vulnerabilità": [
            "no_root_squash — root remoto = root locale → privilege escalation immediata",
            "Nessuna autenticazione interna — si fida del UID/GID del client (falsificabile)",
            "Export aperti a 0.0.0.0/0 — chiunque può montare le share da qualsiasi IP",
            "Disallineamento UID — utente 1001 su client ≠ utente 1001 su server → accessi incrociati",
            "insecure — accetta connessioni da porte sopra 1024 (bypass restrizioni)",
            "root_squash attivo → non puoi modificare file anche se root (attenzione alla verifica)",
        ],
        "enumerazione": [
            "# === RILEVAMENTO ===",
            "showmount -e <IP>                                    # Lista export: chi può accedere e a cosa",
            "sudo nmap -p111,2049 -sV -sC <IP>                   # Scan porte NFS/RPC",
            "sudo nmap --script nfs* -sV -p111,2049 <IP>         # Script NSE: export, permessi, vuln note",
            "",
            "# === MONTARE UNA SHARE ===",
            "sudo mkdir -p /mnt/target_nfs                        # Crea punto di mount locale",
            "sudo mount -t nfs <IP>:/<share> /mnt/target_nfs -o nolock  # Monta la share (-o nolock se NLM non attivo)",
            "",
            "# === ESPLORAZIONE ===",
            "ls -la /mnt/target_nfs                               # Esplora con username/groupname",
            "ls -n /mnt/target_nfs                                # Mostra UID/GID numerici (verifica permessi)",
            "tree /mnt/target_nfs                                 # Struttura completa ad albero",
            "",
            "# === SMONTARE ===",
            "cd ~ && sudo umount /mnt/target_nfs                  # Smonta quando finito (esci prima dalla dir!)",
        ],
        "tool_consigliati": ["nmap"],
    },
    "dns": {
        "nome": "DNS — Domain Name System",
        "porte": "53 (TCP/UDP)",
        "categoria": "DNS & Ricognizione",
        "descrizione": (
            "Sistema per la risoluzione dei nomi di dominio in indirizzi IP.\n"
            "Distribuito globalmente, non ha un database centrale. Ogni server ha un ruolo:\n"
            "\n"
            "  Root Server (13 nel mondo) → Authoritative NS → Caching/Forwarding → Resolver locale\n"
            "\n"
            "Record DNS: A (IPv4), AAAA (IPv6), MX (mail), NS (nameserver), TXT (verifica/SPF/DKIM),\n"
            "            CNAME (alias), PTR (reverse), SOA (info zona).\n"
            "\n"
            "Zona DNS ≠ Record DNS: la zona è il 'contenitore' (es. hackthebox.com) con tutti i record.\n"
            "Il record è la singola riga (es. A → 142.250.184.206). Le zone hanno un SOA, i record no.\n"
            "\n"
            "DNS viaggia in chiaro per default. Soluzioni: DoT (DNS over TLS), DoH (DNS over HTTPS), DNSCrypt.\n"
            "Il browser cerca prima in /etc/hosts, poi contatta i DNS server."
        ),
        "configurazione": [
            "Server comune: BIND9 — config in named.conf (diviso in opzioni + zone)",
            "File locali: named.conf.local, named.conf.options, named.conf.log",
            "Vedere zone: cat /etc/bind/named.conf.local",
            "Zone file: cat /etc/bind/db.domain.com (descrive una zona completa, necessita SOA + NS)",
            "Reverse zone: cat /etc/bind/db.10.129.14 (record PTR per IP→dominio)",
            "Se zona mancante/corrotta il server risponde SERVFAIL",
        ],
        "vulnerabilità": [
            "Zone Transfer (AXFR) aperto — scarichi l'intera zona DNS con tutti i sottodomini",
            "allow-recursion aperto a tutti — DNS amplification attack (DDoS reflection)",
            "allow-query senza restrizioni — informazioni esposte a chiunque",
            "DNS in chiaro — query intercettabili senza DoT/DoH (chiunque in rete vede i siti visitati)",
            "Subdomain takeover — sottodomini che puntano a risorse abbandonate (es. vecchio S3 bucket)",
            "DNS cache poisoning — reindirizzamento a siti malevoli",
        ],
        "enumerazione": [
            "# === QUERY MANUALI CON dig ===",
            "dig domain.com                                       # Record A (default)",
            "dig domain.com A                                     # IPv4",
            "dig domain.com AAAA                                  # IPv6",
            "dig domain.com MX                                    # Mail servers",
            "dig domain.com NS                                    # Name servers autoritativi",
            "dig domain.com TXT                                   # Record TXT (SPF, DKIM, verifiche)",
            "dig domain.com SOA                                   # Start of Authority (admin email, refresh)",
            "dig domain.com ANY                                   # Tutti i record (spesso ignorato per RFC 8482)",
            "dig @1.1.1.1 domain.com                              # Query a DNS specifico (Cloudflare)",
            "dig +trace domain.com                                # Percorso risoluzione completo (root→TLD→auth)",
            "dig -x 192.168.1.1                                   # Reverse lookup (IP→dominio)",
            "dig +short domain.com                                # Solo la risposta, nient'altro",
            "dig +noall +answer domain.com                        # Solo la sezione 'answer'",
            "dig CH TXT version.bind @<DNS_SERVER>                # Versione server DNS",
            "",
            "# === ZONE TRANSFER ===",
            "dig axfr @<DNS_SERVER> <dominio>                     # Full zone transfer (se permesso)",
            "",
            "# === BRUTE FORCE SOTTODOMINI ===",
            "# Manuale con bash + SecLists:",
            "for sub in $(cat /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt);do dig $sub.<dominio> @<IP> | grep -v ';\\|SOA' | sed -r '/^\\s*$/d' | grep $sub | tee -a subdomains.txt;done",
            "",
            "# Con dnsenum (automatico: AXFR + brute force + reverse + whois):",
            "dnsenum --dnsserver <IP> --enum -p 0 -s 0 -o subdomains.txt -f /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt <dominio>",
            "",
            "# Con gobuster (VHost fuzzing — trova virtual host nascosti):",
            "gobuster vhost -u http://<dominio> -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt --append-domain",
            "",
            "# === FONTI PASSIVE (OSINT) ===",
            "curl -s 'https://crt.sh/?q=<dominio>&output=json' | jq -r '.[].name_value' | sort -u  # Certificati SSL",
            "# subdomainfinder.c99.nl — trova sottodomini da fonti pubbliche",
        ],
        "tool_consigliati": ["nmap", "dnsenum", "gobuster", "theHarvester", "recon-ng", "whois", "seclists"],
    },
    "smtp": {
        "nome": "SMTP — Simple Mail Transfer Protocol",
        "porte": "25 (standard), 587 (submission autenticata), 465 (SMTPS)",
        "categoria": "Email",
        "descrizione": (
            "Protocollo per l'invio di email. Spesso combinato con IMAP/POP3 per la lettura.\n"
            "Trasmette dati in chiaro senza SSL/TLS. ESMTP è la versione moderna con STARTTLS.\n"
            "\n"
            "Flusso email: MUA (client) → MSA (verifica auth) → MTA (postino, cerca DNS) → MDA (consegna) → Mailbox (POP3/IMAP)\n"
            "\n"
            "Meccanismi di sicurezza:\n"
            "  SMTP-Auth: obbliga username+password prima di inviare\n"
            "  STARTTLS: attiva crittografia TLS dopo la connessione\n"
            "  SPF: specifica quali server possono inviare per un dominio\n"
            "  DKIM: firma digitale sul messaggio (integrità)\n"
            "  DMARC: policy che combina SPF+DKIM"
        ),
        "configurazione": [
            "Server comune: Postfix — config in /etc/postfix/main.cf",
            "Vedere config: cat /etc/postfix/main.cf | grep -v '#' | sed -r '/^\\s*$/d'",
        ],
        "vulnerabilità": [
            "Open Relay (mynetworks=0.0.0.0/0) — chiunque nel mondo può inviare email dal server",
            "VRFY/EXPN abilitati — enumerazione utenti validi sul server",
            "Dati in chiaro — credenziali intercettabili senza STARTTLS",
            "Mancanza SPF/DKIM/DMARC — email spoofing facilissimo (phishing)",
            "Versioni obsolete di Postfix/Sendmail con exploit noti",
        ],
        "enumerazione": [
            "# === SCAN ===",
            "sudo nmap -sV -sC -p25 <IP>                         # Scan SMTP base",
            "sudo nmap -p25 --script smtp-open-relay -v <IP>      # Verifica open relay",
            "",
            "# === CONNESSIONE MANUALE (telnet) ===",
            "telnet <IP> 25                                       # Connessione diretta",
            "  > EHLO mail1                                       # Inizia sessione (mostra funzionalità)",
            "  > VRFY admin                                       # Verifica se utente esiste (code 252 = ambiguo)",
            "  > EXPN admin                                       # Espandi mailing list",
            "  > MAIL FROM: <test@test.com>                       # Imposta mittente",
            "  > RCPT TO: <admin@target.com>                      # Imposta destinatario",
            "  > DATA                                             # Inizia corpo email (termina con '.')",
            "  > RSET                                             # Annulla trasmissione (mantieni connessione)",
            "  > QUIT                                             # Chiudi sessione",
            "",
            "# === ENUMERAZIONE UTENTI (Metasploit) ===",
            "msfconsole > search smtp_enum > use 0 > set RHOSTS <IP> > set USER_FILE wordlist.txt > run",
        ],
        "tool_consigliati": ["nmap", "theHarvester"],
    },
    "imap-pop3": {
        "nome": "IMAP/POP3 — Protocolli di lettura email",
        "porte": "143 (IMAP), 110 (POP3), 993 (IMAPS), 995 (POP3S)",
        "categoria": "Email",
        "descrizione": (
            "IMAP: le email restano sul server e si sincronizzano su tutti i dispositivi in tempo reale.\n"
            "POP3: scarica le email in locale e le cancella dal server. No sincronizzazione multi-device.\n"
            "\n"
            "IMAP è il più flessibile (cartelle, stato messaggi). POP3 è più semplice.\n"
            "Entrambi viaggiano in chiaro sulle porte standard (143/110).\n"
            "Le porte cifrate sono 993 (IMAPS) e 995 (POP3S).\n"
            "\n"
            "Per testing locale: pacchetti dovecot-imapd e dovecot-pop3d."
        ),
        "configurazione": [
            "Server comune: Dovecot",
        ],
        "vulnerabilità": [
            "auth_debug_passwords=yes — password scritte nei log in chiaro!",
            "auth_verbose_passwords=yes — password nei log (anche troncate)",
            "Autenticazione anonima (SASL ANONYMOUS) — accesso senza credenziali",
            "Connessione in chiaro (porte 143/110) — credenziali sniffabili",
            "Email con chiavi SSH o password nel body → leggi FETCH BODY[TEXT]!",
        ],
        "enumerazione": [
            "# === SCAN ===",
            "sudo nmap -sV -p110,143,993,995 -sC <IP>            # Scan tutte le porte email",
            "",
            "# === CONNESSIONE CON curl ===",
            "curl -k 'imaps://<IP>' --user user:password           # Login IMAP con curl",
            "curl -k 'imaps://<IP>' --user user:password -v        # Verbose (dettagli TLS, banner)",
            "curl -k 'imaps://<IP>/INBOX;UID=1' --user user:pass   # Leggi email specifica per UID",
            "",
            "# === CONNESSIONE CIFRATA ===",
            "openssl s_client -connect <IP>:imaps -crlf            # IMAP over SSL",
            "openssl s_client -connect <IP>:pop3s                  # POP3 over SSL",
            "",
            "# === COMANDI IMAP (dopo connessione) ===",
            "  1 LOGIN user password                              # Autenticazione",
            "  1 LIST \"\" *                                         # Lista tutte le cartelle",
            "  1 SELECT INBOX                                      # Seleziona inbox",
            "  1 FETCH <ID> all                                   # Header + metadata email",
            "  1 FETCH 1 (BODY[TEXT])                              # Corpo email → CERCA CHIAVI SSH!",
            "  1 CLOSE                                             # Rimuovi email marcate come eliminate",
            "  1 LOGOUT                                            # Disconnetti",
            "",
            "# === COMANDI POP3 ===",
            "  USER username > PASS password > STAT > LIST > RETR 1 > DELE 1 > QUIT",
        ],
        "tool_consigliati": ["nmap"],
    },
    "snmp": {
        "nome": "SNMP — Simple Network Management Protocol",
        "porte": "161/UDP (query), 162/UDP (trap)",
        "categoria": "Monitoraggio Rete",
        "descrizione": (
            "Protocollo per monitorare e gestire dispositivi di rete (router, switch, server, stampanti).\n"
            "\n"
            "Componenti: SNMP (trasporto) + MIB (dizionario dati del dispositivo) + OID (coordinate univoche per ogni dato).\n"
            "Ogni OID è una catena di numeri (es. .1.3.6.1.2.1.1.1.0 = nome sistema).\n"
            "Più la catena è lunga, più l'info è specifica.\n"
            "\n"
            "Versioni:\n"
            "  SNMPv1: nessuna crittografia né auth reale. Tutto intercettabile.\n"
            "  SNMPv2c: introduce la Community String (password in chiaro). La più diffusa.\n"
            "  SNMPv3: username + password + crittografia. Sicura ma complessa da configurare.\n"
            "\n"
            "Trap (porta 162): notifiche automatiche dal dispositivo senza richiesta."
        ),
        "configurazione": [
            "Config: /etc/snmp/snmpd.conf",
            "Vedere config: cat /etc/snmp/snmpd.conf | grep -v '#' | sed -r '/^\\s*$/d'",
        ],
        "vulnerabilità": [
            "Community string di default (public/private) — accesso totale ai dati del dispositivo",
            "rwuser noauth — lettura/scrittura su tutto l'albero OID senza autenticazione",
            "rwcommunity aperta — modifica OID tree (config dispositivo) senza limiti",
            "SNMPv1/v2c in chiaro — community string intercettabile con uno sniffer",
            "Esposizione info: processi in esecuzione, software installati, utenti, config di rete completa",
        ],
        "enumerazione": [
            "# === BRUTE FORCE COMMUNITY STRING ===",
            "onesixtyone -c /usr/share/seclists/Discovery/SNMP/snmp.txt <IP>",
            "",
            "# === ESTRAZIONE DATI (una volta trovata la community string) ===",
            "snmpwalk -v2c -c public <IP>                          # Tutti gli OID (lento, uno per uno)",
            "braa public@<IP>:.1.3.6.*                             # Scan parallelo (MOLTO più veloce)",
            "braa <community>@<IP>:.1.3.6.*                        # Con community personalizzata",
            "",
            "# === NMAP ===",
            "sudo nmap -sU -p161 --script snmp-info <IP>           # Info SNMP base",
        ],
        "tool_consigliati": ["nmap", "onesixtyone", "braa", "seclists"],
    },
    "mysql": {
        "nome": "MySQL — Database Relazionale",
        "porte": "3306 (TCP)",
        "categoria": "Database",
        "descrizione": (
            "Database relazionale open source. Architettura client-server.\n"
            "Molto diffuso nelle applicazioni web (LAMP stack: Linux + Apache + MySQL + PHP).\n"
            "I client usano query SQL per accedere/modificare i dati."
        ),
        "configurazione": [
            "Installazione: sudo apt install mysql-server -y",
            "Config: /etc/mysql/mysql.conf.d/mysqld.cnf",
            "Vedere config: cat /etc/mysql/mysql.conf.d/mysqld.cnf | grep -v '#' | sed -r '/^\\s*$/d'",
        ],
        "vulnerabilità": [
            "Root senza password — accesso amministratore totale al database",
            "debug/sql_warnings attivi — messaggi dettagliati rivelano struttura DB (utile per SQL injection)",
            "secure_file_priv mal configurato — lettura/scrittura file del sistema operativo via MySQL",
            "Credenziali nel file di configurazione con permessi troppo aperti → password in chiaro",
            "admin_address esposto su Internet → attaccabile da chiunque",
        ],
        "enumerazione": [
            "# === SCAN ===",
            "sudo nmap -sV -sC -p3306 --script mysql* <IP>        # Scan + tutti gli script NSE MySQL",
            "",
            "# === CONNESSIONE ===",
            "mysql -u root -h <IP>                                 # Tentativo senza password",
            "mysql -u root -p'P4SSw0rd' -h <IP>                   # Con password",
            "mysql -u root -p'P4SSw0rd' -h <IP> --skip-ssl        # Se SSL dà problemi",
            "",
            "# === COMANDI UTILI DENTRO MYSQL ===",
            "  show databases;                                     # Lista tutti i database",
            "  use <database>;                                     # Seleziona un database",
            "  show tables;                                        # Lista tabelle",
            "  show columns from <table>;                          # Struttura di una tabella",
            "  select * from <table>;                              # Tutti i dati",
            "  select * from <table> where <col> = '<val>';        # Filtra per valore",
            "  use sys; select host, unique_users from host_summary;  # Chi si connette da dove",
        ],
        "tool_consigliati": ["nmap"],
    },
    "mssql": {
        "nome": "MSSQL — Microsoft SQL Server",
        "porte": "1433 (TCP)",
        "categoria": "Database",
        "descrizione": (
            "Database relazionale Microsoft, integrato con .NET e Active Directory.\n"
            "Client principale: SSMS (SQL Server Management Studio) — GUI per admin.\n"
            "Da Linux: mssqlclient.py (Impacket) o mssql-cli.\n"
            "\n"
            "Database di sistema: master (config), model (template), msdb (job/backup), tempdb (dati temporanei).\n"
            "ATTENZIONE: SSMS a volte salva le password in chiaro sul PC dell'admin!"
        ),
        "configurazione": [],
        "vulnerabilità": [
            "Utente sa (System Administrator) con password debole o di default",
            "Autenticazione Windows — account rubato = accesso automatico al DB",
            "xp_cmdshell abilitato — esecuzione comandi di sistema dal database → RCE",
            "Certificati non validati — intercettazione connessione (MitM)",
            "SSMS salva password in chiaro sul PC dell'admin",
            "Nessuna cifratura tra client e server per default",
        ],
        "enumerazione": [
            "# === SCAN COMPLETO CON NMAP ===",
            "sudo nmap --script ms-sql-info,ms-sql-empty-password,ms-sql-xp-cmdshell,\\",
            "ms-sql-config,ms-sql-ntlm-info,ms-sql-tables,ms-sql-hasdbaccess,\\",
            "ms-sql-dac,ms-sql-dump-hashes \\",
            "--script-args mssql.instance-port=1433,mssql.username=sa,mssql.password=,\\",
            "mssql.instance-name=MSSQLSERVER -sV -p 1433 <IP>",
            "",
            "# === CONNESSIONE CON IMPACKET ===",
            "python3 mssqlclient.py Administrator@<IP> -windows-auth  # Auth Windows",
            "python3 mssqlclient.py sa@<IP>                            # Auth SQL diretta",
            "",
            "# === NETEXEC ===",
            "nxc mssql <IP> -u 'sa' -p 'password' --query 'SELECT @@version;'",
        ],
        "tool_consigliati": ["nmap", "impacket", "crackmapexec"],
    },
    "oracle-tns": {
        "nome": "Oracle TNS — Transparent Network Substrate",
        "porte": "1521 (TCP)",
        "categoria": "Database",
        "descrizione": (
            "Protocollo di comunicazione tra applicazioni e database Oracle.\n"
            "Il Listener accetta connessioni sulla porta 1521.\n"
            "\n"
            "Config client: tnsnames.ora  |  Config server: listener.ora\n"
            "Percorso config: $ORACLE_HOME/network/admin\n"
            "\n"
            "Per connettersi serve il SID (Service Identifier) — se non lo conosci, brute force."
        ),
        "configurazione": [
            "Config client: $ORACLE_HOME/network/admin/tnsnames.ora",
            "Config server: $ORACLE_HOME/network/admin/listener.ora",
        ],
        "vulnerabilità": [
            "SID indovinabile — brute force del Service Identifier con Nmap",
            "Credenziali di default (scott/tiger, sys/change_on_install)",
            "utlfile — upload file sul server (web shell in /var/www/html o C:\\inetpub\\wwwroot)",
            "sysdba senza restrizioni — 'as sysdba' bypassa i controlli → privilege escalation",
            "Hash password estraibili da sys.user$ → crackabili offline",
        ],
        "enumerazione": [
            "# === RILEVAMENTO ===",
            "sudo nmap -p1521 -sV <IP> --open                     # Rileva Oracle TNS",
            "sudo nmap -p1521 --script oracle-sid-brute <IP>       # Brute force SID",
            "",
            "# === ENUMERAZIONE CON ODAT ===",
            "./odat.py all -s <IP>                                 # Enumerazione completa (trova user, vuln, SID)",
            "",
            "# === CONNESSIONE CON sqlplus ===",
            "sqlplus <user>/<pass>@<IP>/<SID>                      # Login standard",
            "sqlplus <user>/<pass>@<IP>/<SID> as sysdba            # Login come admin (privilege escalation!)",
            "",
            "# === COMANDI UTILI ===",
            "  select table_name from all_tables;                  # Lista tutte le tabelle",
            "  select * from user_role_privs;                      # Verifica i tuoi privilegi",
            "  select name, password from sys.user$;               # Dump hash password di TUTTI gli utenti",
            "",
            "# === UPLOAD FILE (Web Shell) ===",
            "# Linux:",
            "./odat.py utlfile -s <IP> -d <SID> -U <user> -P <pass> --sysdba --putFile /var/www/html shell.txt ./shell.txt",
            "# Windows:",
            "./odat.py utlfile -s <IP> -d <SID> -U <user> -P <pass> --sysdba --putFile C:\\\\inetpub\\\\wwwroot shell.txt ./shell.txt",
            "curl -X GET http://<IP>/shell.txt                     # Verifica upload",
        ],
        "tool_consigliati": ["nmap", "odat"],
    },
    "ipmi": {
        "nome": "IPMI — Intelligent Platform Management Interface",
        "porte": "623 (UDP)",
        "categoria": "Hardware & Management",
        "descrizione": (
            "Interfaccia per gestire server da remoto, ANCHE SE SPENTI (basta che siano attaccati alla corrente).\n"
            "Indipendente da CPU, BIOS e sistema operativo — funziona tramite il BMC (Baseboard Management Controller).\n"
            "\n"
            "Nomi commerciali: HP = iLO, Dell = iDRAC, Supermicro = IPMI.\n"
            "\n"
            "Permette: accensione/spegnimento remoto, modifica BIOS, monitoraggio hardware (temp, ventole),\n"
            "reinstallazione OS da remoto come se inserissi una chiavetta USB fisicamente."
        ),
        "configurazione": [],
        "vulnerabilità": [
            "Password di default — Dell: root/calvin, Supermicro: ADMIN/ADMIN, HP iLO: bollino dietro il server",
            "Difetto protocollo RAKP (vers. 2.0) — il server invia l'hash della password PRIMA dell'autenticazione!",
            "Hash crackabili con hashcat -m 7300 (difetto di progettazione, non riparabile con aggiornamento)",
            "Interfaccia web spesso esposta su Internet senza restrizioni",
            "Firmware raramente aggiornato — vecchie CVE persistenti",
        ],
        "enumerazione": [
            "# === RILEVAMENTO ===",
            "sudo nmap -sU --script ipmi-version -p 623 <IP>      # Rileva versione IPMI",
            "",
            "# === METASPLOIT — versione IPMI ===",
            "msfconsole > use auxiliary/scanner/ipmi/ipmi_version > set RHOSTS <IP> > run",
            "",
            "# === METASPLOIT — dump hash (sfrutta difetto RAKP) ===",
            "msfconsole > use auxiliary/scanner/ipmi/ipmi_dumphashes > set RHOSTS <IP> > run",
            "",
            "# === CRACK HASH CON HASHCAT ===",
            "hashcat -m 7300 ipmi.txt -a 3 ?1?1?1?1?1?1?1?1 -1 ?d?u  # Brute force con mask",
            "hashcat -a 0 -m 7300 ipmi.txt /usr/share/wordlists/rockyou.txt  # Con wordlist",
        ],
        "tool_consigliati": ["nmap", "hashcat"],
    },
    "ssh": {
        "nome": "SSH — Secure Shell",
        "porte": "22 (TCP)",
        "categoria": "Accesso Remoto",
        "descrizione": (
            "Protocollo per connessioni remote cifrate. Standard per amministrazione Linux/Unix.\n"
            "SSH-1 è insicuro (vulnerabile a MitM). SSH-2 è lo standard attuale.\n"
            "\n"
            "6 metodi di autenticazione:\n"
            "  1. Password  2. Public Key  3. Host-based  4. Keyboard  5. Challenge-Response  6. GSSAPI (Kerberos)\n"
            "\n"
            "Chiavi SSH: la chiave privata (id_rsa) DEVE restare segreta.\n"
            "Se trovi accesso a /home/user/.ssh/id_rsa puoi usarla per loggarti.\n"
            "Alcune chiavi sono cifrate con passphrase → crackabili con ssh2john + JtR."
        ),
        "configurazione": [
            "Config server: /etc/ssh/sshd_config",
            "Vedere config: cat /etc/ssh/sshd_config | grep -v '#' | sed -r '/^\\s*$/d'",
        ],
        "vulnerabilità": [
            "PermitRootLogin yes — accesso diretto come root da remoto",
            "PermitEmptyPasswords yes — login senza password (devastante)",
            "Protocol 1 — crittografia obsoleta, vulnerabile a MitM",
            "X11Forwarding yes — command injection in alcune versioni",
            "Password deboli — brute force con hydra/medusa",
            "Chiavi private esposte (id_rsa senza passphrase in share NFS/FTP/email)",
            "DebianBanner yes — mostra versione OS esatta (aiuta a scegliere exploit)",
        ],
        "enumerazione": [
            "# === AUDIT CONFIGURAZIONE ===",
            "./ssh-audit.py <IP>                                   # Audit completo (cifrari, KEX, chiavi host)",
            "ssh -v user@<IP>                                      # Connessione verbose (vedi metodi auth)",
            "ssh -v user@<IP> -o PreferredAuthentications=password  # Forza autenticazione password",
            "sudo nmap -sV -p22 --script ssh* <IP>                 # Script NSE SSH",
            "",
            "# === BRUTE FORCE ===",
            "hydra -l root -P /usr/share/wordlists/rockyou.txt ssh://<IP>",
            "",
            "# === CHIAVI SSH ===",
            "# Se trovi una chiave privata (id_rsa):",
            "chmod 600 id_rsa                                      # Permessi restrittivi (obbligatorio)",
            "ssh root@<IP> -i id_rsa                               # Login con chiave rubata",
            "",
            "# Per cercare chiavi nel filesystem:",
            "grep -rnE '^\\-{5}BEGIN [A-Z0-9]+ PRIVATE KEY\\-{5}$' /* 2>/dev/null",
            "",
            "# Se la chiave è cifrata con passphrase:",
            "ssh-keygen -yf id_rsa                                 # Verifica se ha passphrase",
            "ssh2john.py id_rsa > ssh.hash                         # Estrai hash per JtR",
            "john --wordlist=rockyou.txt ssh.hash                  # Crack passphrase",
            "john ssh.hash --show                                  # Mostra risultato",
            "",
            "# === PERSISTENZA ===",
            "# Se hai accesso in scrittura a /home/user/.ssh/:",
            "# Aggiungi la TUA chiave pubblica in authorized_keys → accesso permanente",
        ],
        "tool_consigliati": ["nmap", "ssh-audit", "john", "hashcat", "seclists"],
    },
    "rdp": {
        "nome": "RDP — Remote Desktop Protocol",
        "porte": "3389 (TCP)",
        "categoria": "Accesso Remoto",
        "descrizione": (
            "Protocollo Microsoft per il controllo remoto del desktop (GUI completa).\n"
            "Dati cifrati ma spesso con certificati autofirmati → il PC non può verificare\n"
            "se si sta connettendo al server giusto o a un impostore (MitM possibile)."
        ),
        "configurazione": [],
        "vulnerabilità": [
            "BlueKeep (CVE-2019-0708) — RCE pre-auth su vecchi Windows (XP, 7, Server 2008)",
            "Certificati autofirmati — MitM attack (intercettazione desktop remoto)",
            "NLA disabilitato — attacchi brute force facilitati (nessun pre-auth)",
            "Credenziali deboli — brute force con hydra/nxc",
            "Session hijacking — furto sessioni RDP attive",
        ],
        "enumerazione": [
            "# === SCAN ===",
            "nmap -sV -sC -p3389 --script rdp* <IP>               # Scan + script RDP",
            "nmap -sV -sC -p3389 --packet-trace --disable-arp-ping -n <IP>  # Dettagliato",
            "",
            "# === VERIFICA SICUREZZA ===",
            "./rdp-sec-check.pl <IP>                               # Check cifrari, NLA, auth level",
            "",
            "# === VERIFICA CREDENZIALI ===",
            "nxc rdp <IP> -u 'admin' -p 'password'                 # Singolo tentativo",
            "nxc rdp <SUBNET>/24 -u users.txt -p 'Password123!'   # Password spraying su rete",
            "",
            "# === CONNESSIONE ===",
            "xfreerdp /u:user /p:'password' /v:<IP> /cert:ignore /dynamic-resolution +clipboard",
            "# Opzioni utili: /drive:share,/tmp (monta cartella locale) /sec:tls (forza TLS)",
        ],
        "tool_consigliati": ["nmap", "rdp-sec-check", "crackmapexec"],
    },
    "winrm": {
        "nome": "WinRM — Windows Remote Management",
        "porte": "5985 (HTTP), 5986 (HTTPS)",
        "categoria": "Accesso Remoto",
        "descrizione": (
            "Protocollo Microsoft per esecuzione comandi remoti via riga di comando (PowerShell).\n"
            "Basato su WS-Management. A differenza di RDP, non mostra il desktop — solo terminale.\n"
            "Porta 5985 (HTTP, in chiaro!) e 5986 (HTTPS, cifrato)."
        ),
        "configurazione": [],
        "vulnerabilità": [
            "Credenziali deboli — shell PowerShell completa con accesso admin",
            "Pass-the-Hash — autenticazione con hash NTLM rubato (non serve la password in chiaro)",
            "HTTP (5985) in chiaro — credenziali intercettabili sulla rete",
            "Accesso diretto a PowerShell — esecuzione codice arbitrario, download malware",
        ],
        "enumerazione": [
            "# === SCAN ===",
            "nmap -sV -sC -p5985,5986 --disable-arp-ping -n <IP>  # Scan porte WinRM",
            "",
            "# === VERIFICA CREDENZIALI ===",
            "nxc winrm <IP> -u 'user' -p 'password'               # Test login (Pwn3d! = admin locale!)",
            "nxc winrm <IP> -u 'user' -p 'password' -x 'hostname' # Esegui comando remoto",
            "",
            "# === SHELL INTERATTIVA ===",
            "evil-winrm -i <IP> -u 'user' -p 'password'           # Shell PowerShell completa",
            "evil-winrm -i <IP> -u 'user' -H 'HASH_NTLM'         # Pass-the-Hash (senza password!)",
            "",
            "# === COMANDI UTILI DENTRO LA SHELL ===",
            "  Get-LocalUser                                       # Lista utenti locali Windows",
            "  Get-LocalGroup                                      # Lista gruppi",
            "  Get-Process                                         # Processi attivi",
        ],
        "tool_consigliati": ["nmap", "evil-winrm", "crackmapexec"],
    },
    "wmi": {
        "nome": "WMI — Windows Management Instrumentation",
        "porte": "135 (TCP)",
        "categoria": "Accesso Remoto",
        "descrizione": (
            "Insieme di strumenti per gestire qualsiasi impostazione di Windows da remoto:\n"
            "RAM, processi, software installati, configurazioni, servizi.\n"
            "Porta TCP 135. Usa wmiexec.py di Impacket per connettersi da Linux.\n"
            "Spesso non monitorato dai sistemi di difesa → attività difficile da rilevare."
        ),
        "configurazione": [],
        "vulnerabilità": [
            "Credenziali admin — controllo totale del sistema Windows",
            "Esecuzione comandi remoti — RCE immediata con qualsiasi utente privilegiato",
            "Spesso non monitorato da IDS/SIEM — attività invisibile nei log standard",
        ],
        "enumerazione": [
            "# === CONNESSIONE CON IMPACKET ===",
            "python3 wmiexec.py user:'password'@<IP> 'hostname'    # Esegui comando remoto",
            "python3 wmiexec.py user:'password'@<IP> 'whoami'      # Chi sono sul target?",
            "python3 wmiexec.py user:'password'@<IP> 'ipconfig /all'  # Configurazione rete completa",
            "",
            "# === CON NETEXEC ===",
            "nxc smb <IP> -u 'user' -p 'password' -x 'whoami'     # Esecuzione via SMB/WMI",
        ],
        "tool_consigliati": ["impacket", "crackmapexec"],
    },
}

VULN_ALIASES: dict[str, str] = {
    "imap": "imap-pop3",
    "pop3": "imap-pop3",
    "pop": "imap-pop3",
    "imap pop3": "imap-pop3",
    "imap/pop3": "imap-pop3",
    "oracle": "oracle-tns",
    "tns": "oracle-tns",
    "oracletns": "oracle-tns",
    "oracle tns": "oracle-tns",
    "samba": "smb",
    "cifs": "smb",
    "netbios": "smb",
    "rpc": "smb",
    "ftps": "ftp",
    "tftp": "ftp",
    "sftp": "ftp",
    "vsftpd": "ftp",
    "bind": "dns",
    "bind9": "dns",
    "nslookup": "dns",
    "dig": "dns",
    "sshd": "ssh",
    "openssh": "ssh",
    "mstsc": "rdp",
    "xfreerdp": "rdp",
    "rdesktop": "rdp",
    "idrac": "ipmi",
    "ilo": "ipmi",
    "bmc": "ipmi",
    "postfix": "smtp",
    "sendmail": "smtp",
    "dovecot": "imap-pop3",
    "nfsd": "nfs",
    "portmapper": "nfs",
    "mssqlserver": "mssql",
    "sqlserver": "mssql",
    "mariadb": "mysql",
    "mysqld": "mysql",
}


def cmd_vuln(args: argparse.Namespace, state: ConsoleState | None = None) -> int:
    raw = " ".join(args.protocol) if isinstance(args.protocol, list) else args.protocol
    key = normalize(raw)

    if key in {"list", "*", "all"}:
        print("\nProtocolli disponibili per 'vuln':\n")
        for cat_name, cat_protos in VULN_CATEGORIES.items():
            print(f"  [{cat_name}]")
            for proto_key in cat_protos:
                proto_data = VULN_DB[proto_key]
                print(f"    {proto_key:<14} {proto_data['nome']:<45} Porte: {proto_data['porte']}")
            print()
        print(f"  Alias supportati: {', '.join(sorted(VULN_ALIASES.keys()))}")
        print()
        return 0

    key = VULN_ALIASES.get(key, key)

    if key not in VULN_DB:
        print(f"Protocollo '{raw}' non trovato.", file=sys.stderr)
        print("Usa 'vuln list' per vedere i protocolli disponibili.")
        return 1

    proto = VULN_DB[key]
    sep = "=" * 70

    text_parts = [
        f"\n{sep}",
        f"  {proto['nome']}",
        f"  Porte: {proto['porte']}",
        f"  Categoria: {proto.get('categoria', 'N/D')}",
        sep,
        "",
        proto["descrizione"],
    ]

    if proto.get("configurazione"):
        text_parts.extend(["", "--- CONFIGURAZIONE ---", ""])
        for c in proto["configurazione"]:
            text_parts.append(f"  {c}")

    text_parts.extend(["", "--- VULNERABILITÀ COMUNI ---", ""])
    for v in proto["vulnerabilità"]:
        text_parts.append(f"  • {v}")

    text_parts.extend(["", "--- ENUMERAZIONE & COMANDI ---", ""])
    for cmd in proto["enumerazione"]:
        text_parts.append(f"  {cmd}")

    if proto["tool_consigliati"]:
        text_parts.extend(["", "--- TOOL CONSIGLIATI (installa con 'use <tool>' + 'install') ---", ""])
        for t in proto["tool_consigliati"]:
            installed = "✓" if which(t) else " "
            text_parts.append(f"  [{installed}] {t}")

    text_parts.extend(["", sep, ""])
    print("\n".join(text_parts))
    return 0


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        return run_console()

    if len(argv) == 1 and argv[0] in {"-h", "--help"}:
        print_banner()
        print_help_text()
        return 0

    if len(argv) == 1 and argv[0] == "--version":
        print(f"{APP_NAME} {VERSION}")
        return 0

    return run_command(argv, ConsoleState())


if __name__ == "__main__":
    raise SystemExit(main())
