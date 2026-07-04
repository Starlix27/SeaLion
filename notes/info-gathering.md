# Information Gathering & Ricognizione

## Obiettivi della Ricognizione

- **Identificare gli asset:** Trovare tutte le "entrate" (pagine web, sottodomini, indirizzi IP)
- **Scoprire informazioni nascoste:** Cercare file dimenticati o documenti interni
- **Analizzare la superficie di attacco:** Capire quali tecnologie usa il sito per trovare punti deboli
- **Raccogliere intelligence:** Trovare nomi di dipendenti o email per social engineering

## Ricognizione Attiva vs Passiva

### Ricognizione Attiva
- Interagisci direttamente con il server del bersaglio
- **Esempi:** Scansionare le porte (Nmap), crawler/spidering
- **Rischio:** Alto. IDS/Firewall potrebbero rilevare l'attività

### Ricognizione Passiva (OSINT)
- Raccogli informazioni senza toccare il server
- **Google Hacking**, **WHOIS**, **Wayback Machine**, **Social Media**
- **Rischio:** Bassissimo. Il bersaglio non saprà mai che lo stai studiando

---

## WHOIS

- Per ottenere informazioni del dominio di un'azienda
- Utile per social engineering, scoprire la mail del registrante, analisi infrastruttura
- Molto spesso ci sono restrizioni GDPR, ma i vecchi record sono conservati su whoisfreaks.com

```bash
sudo apt install whois
whois nome-dominio.com
```

Segnali di affidabilità di un dominio:
1. **Anzianità:** Creato da molto tempo
2. **Proprietà chiara:** Registrante esplicito (es. "Meta Platforms, Inc.")
3. **Stato di blocco:** `clientTransferProhibited` = dominio blindato

---

## Virtual Hosts

Il server web è come un condominio con un unico indirizzo (IP). I Virtual Host gestiscono quale sito servire grazie all'**Host Header**.

### Sottodominio vs Virtual Host
- **Sottodominio:** Gestione legata al DNS (es. `shop.sito.com`)
- **Virtual Host:** Configurazione interna al server

### Tipi di Virtual Hosting

| Tipo | Come funziona | Pro & Contro |
|------|---------------|--------------|
| **Name-Based** | Usa l'Host Header. Stesso IP per tutti i siti | Il più usato, economico |
| **IP-Based** | Ogni sito ha il suo IP dedicato | Sicuro ma costoso |
| **Port-Based** | Stesso IP ma porte diverse | Utile per test, scomodo per utenti |

### VHost Fuzzing con Gobuster
```bash
gobuster vhost -u http://inlanefreight.htb:81 -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt --append-domain
```
- `-t` (Threads): aumenta velocità
- `-k` (Insecure): ignora errori SSL
- `-o` (Output): salva risultati in file

---

## Certificate Transparency Logs

I CT Logs sono registri pubblici di tutti i certificati SSL emessi. Utili per trovare sottodomini senza brute-forcing.

### Strumenti
- **crt.sh** — Sito web gratuito per consultare i log
- **Censys** — Motore di ricerca avanzato per infrastruttura internet

```bash
curl -s "https://crt.sh/?q=facebook.com&output=json" | jq -r '.[] | select(.name_value | contains("dev")) | .name_value' | sort -u
```

---

## Fingerprinting

Identificare il software e le tecnologie dietro un sito web.

### Tecniche
1. **Banner Grabbing:** Leggere i messaggi di benvenuto del server
2. **HTTP Headers:** Analizzare `Server:` e `X-Powered-By:`
3. **Richieste particolari:** Provocare errori per studiare le risposte
4. **Contenuto della pagina:** Cercare strutture di CMS, file di licenza

```bash
# Banner grabbing
curl -I http://target.com

# Controllo WAF
pip3 install git+https://github.com/EnableSecurity/wafw00f
wafw00f inlanefreight.com

# Scansione con Nikto
nikto -h inlanefreight.com -Tuning b
```

---

## Crawling (Spidering)

Esplorazione automatica di un sito seguendo i link.

### Strategie
- **Breadth-First:** Esplora prima tutte le pagine principali (mappa generale)
- **Depth-First:** Segue un link fino in fondo (contenuti nascosti)

### Dati estratti dal crawler
- Link interni/esterni
- Commenti nel codice HTML
- Metadati (autori, date)
- File sensibili (`.bak`, `.old`, `settings.php`, `error_log`)

### Crawler principali
1. **Burp Suite Spider** — Il "coltellino svizzero" del PT
2. **OWASP ZAP** — Alternativa open-source
3. **Scrapy** — Framework Python personalizzabile
4. **Apache Nutch** — Scala industriale

---

## robots.txt

Il file `robots.txt` è la guida di cortesia per i crawler. Si trova in `www.sito.com/robots.txt`.

### Direttive
- `User-agent:` — A quale robot si rivolge (* = tutti)
- `Disallow:` — Pagine che il bot non deve guardare
- `Allow:` — Aree permesse
- `Crawl-delay:` — Pausa tra richieste
- `Sitemap:` — Mappa del sito XML

**Paradosso:** Il file è pubblico. Un `Disallow: /admin/` rivela che `/admin/` esiste.

---

## .well-known URIs

Cartella standardizzata (RFC 8615) per file di configurazione e metadati.

File comuni:
- `security.txt` — Contatti del team di sicurezza
- `change-password` — Link per cambio password
- `openid-configuration` — Configurazione OAuth/OpenID Connect
- `assetlinks.json` — Verifica app Android

---

## Google Dorking

Usare i motori di ricerca come strumento di ricognizione passiva (OSINT).

### Operatori principali

| Operatore | Descrizione | Esempio |
|-----------|-------------|---------|
| `site:` | Limita i risultati a un sito | `site:example.com` |
| `inurl:` | Cerca nell'URL | `inurl:login` |
| `filetype:` | Cerca per tipo di file | `filetype:pdf` |
| `intitle:` | Cerca nel titolo | `intitle:"confidential report"` |
| `intext:` | Cerca nel corpo | `intext:"password reset"` |
| `cache:` | Versione cached | `cache:example.com` |
| `""` | Frase esatta | `"information security policy"` |
| `-` | Esclude termine | `site:news.com -inurl:sports` |

### Esempi pratici
```
# Trovare pagine di login
site:azienda.com (inurl:login OR inurl:admin)

# File aziendali esposti
site:azienda.com (filetype:xls OR filetype:docx)

# File di configurazione
site:azienda.com inurl:config.php
```

Archivio dorks: **Google Hacking Database (GHDB)**

---

## Wayback Machine

Archivio digitale che scatta "fotografie" dei siti web dal 1996 a oggi.

### Vantaggi per la ricognizione
- **Invisibile:** Scarichi dai server di Internet Archive, non dalla vittima
- **File dimenticati:** Pagine vulnerabili rimosse ma archiviate
- **Evoluzione tecnologica:** Confrontare vecchi snapshot
- **OSINT:** Nomi di vecchi dipendenti, vecchie strategie

---

## Framework di Automazione

| Framework | Descrizione |
|-----------|-------------|
| **FinalRecon** | Modulare Python, raccoglie headers, certificati, WHOIS, crawling |
| **Recon-ng** | Console stile Metasploit, espandibile con moduli |
| **theHarvester** | OSINT: email, nomi, sottodomini, porte da motori di ricerca e Shodan |
| **SpiderFoot** | Oltre 100 fonti dati per OSINT completo |
| **OSINT Framework** | Mappa/sito web con tutti i servizi per investigazione digitale |

### FinalRecon
```bash
git clone https://github.com/thewhiteh4t/FinalRecon.git
cd FinalRecon
pip3 install -r requirements.txt
chmod +x ./finalrecon.py
./finalrecon.py --headers --whois --url http://inlanefreight.com
```
