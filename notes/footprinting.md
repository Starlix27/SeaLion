# Metodologia di Enumerazione

Possiamo dividere il processo di enumerazione in:

- **Infrastructure-based**: Guardare la rete dall'esterno
- **Host-based**: Concentrarsi su un singolo pc/server
- **OS-based**: Una volta dentro capire com'è fatto il SO

## I 6 strati della metodologia

### 1. Internet Presence (Presenza online)
- Ottenere i nomi dei domini, indirizzi IP, server cloud ecc…
- L'obiettivo: creare una lista di possibili bersagli

### 2. Gateway
- Prima di toccare i server bisogna capire chi li protegge
- Si cercano firewall, sistemi anti-intrusione IDS/IPS, VPN
- L'obiettivo: capire quali ostacoli attivi ci sono tra te e il bersaglio per schivarli

### 3. Accessible Services
- Una volta individuato il server capire cosa ha
- Si cerca un server web, mail o un db
- Capire cosa fa quella macchina e come interagirci

### 4. Processes
- Ogni servizio (es sito web) fa girare dei servizi
- Si cerca quale programma sta girando, da dove vengono presi i dati e dove li mandano
- L'obiettivo: trovare dipendenze o errori nel modo in cui i dati vengono elaborati

### 5. Privileges
- Ogni programma ha un'identità (utente)
- Si cerca un servizio con permessi (admin o restrizioni) e capire chi può leggere file
- L'obiettivo: capire se puoi sfruttare un servizio per fare una escalation di privilegi

### 6. OS Setup
- Una volta dentro si cerca la versione del SO, aggiornamenti, file di config lasciati aperti
- L'obiettivo: ottenere il controllo totale e vedere come l'azienda ha protetto i propri sistemi interni

---

## Internet Presence

- Raccolta dati passiva, come guest o visitatore
- Guardare il sito web principale e raccogliere info pubbliche utili per il pentesting
- Capire quali tecnologie servono per far funzionare il sito

### Certificati SSL
- Spesso un solo certificato è valido per molti sottodomini (es. `mail.azienda.com`, `vpn.azienda.com`)
- **Fonte:** crt.sh raccoglie i log pubblici di tutti i certificati emessi. Es: `https://crt.sh/?q=inlanefreight.com`
- Ti permette di scoprire nomi di server che l'azienda non ha pubblicizzato

### Shodan
- Motore di ricerca per dispositivi connessi (server, webcam, router ecc…)
- Mostra le porte aperte e le versioni di software in uso
- Dà un'anteprima dei servizi attivi senza che tu debba scansionarli

#### Comandi principali
```bash
# Installazione
pip install shodan
shodan init TUA_API_KEY_QUI

# Analizzare un singolo Host
shodan host 10.129.27.33

# Ricerca generica
shodan search "InlaneFreight"
shodan search "Apache 2.4.41"

# Contare i risultati
shodan count "org:InlaneFreight"

# IP pubblico
shodan myip

# Automazione su lista IP
for i in $(cat ip-addresses.txt); do shodan host $i; done

# Filtro per organizzazione
shodan search org:"Nome Azienda" --fields ip_str,port,org
```

### Record DNS con `dig`
- Interrogando i server DNS con `dig any` otteniamo info dalla rete aziendale
- **Record A:** Gli indirizzi IP diretti dei server
- **Record MX:** Chi gestisce le email (es. Google o Outlook)
- **Record TXT:** Spesso contengono chiavi di verifica per servizi esterni (DMARC, DKIM, SPF)

---

## Cloud Resources

- Molte aziende spostano dati sul Cloud, ma configurazioni errate (permessi "Public") trasformano questi depositi in miniere d'oro

### Identificazione tramite DNS e IP
```bash
for i in $(cat subdomainlist);do host $i | grep "has address" | grep inlanefreight.com | cut -d" " -f1,4;done
```

### Google Dorking per il Cloud
- **AWS:** `site:s3.amazonaws.com "nome_azienda"`
- **Azure:** `site:blob.core.windows.net "nome_azienda"`
- **File sensibili:** `site:s3.amazonaws.com "nome_azienda" filetype:pdf`

### Strumenti per Cloud Recon

| Strumento | Scopo |
|-----------|-------|
| **Domain.glass** | Mostra informazioni sull'infrastruttura e protezioni (es. Cloudflare) |
| **GrayHatWarfare** | Database pubblico di bucket AWS/Azure/GCP. Cerca file specifici (es. `id_rsa`) |

---

> Footprinting wordlist: https://file.ax/8m93ampd
