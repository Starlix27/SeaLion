# Gobuster — Directory/VHost/DNS Fuzzer

**Gobuster** è un tool veloce per il fuzzing di directory, sottodomini DNS e Virtual Host. Scritto in Go, è molto performante.

---

## A cosa serve?

- **Directory Fuzzing:** Trova cartelle e file nascosti su web server
- **VHost Fuzzing:** Scopre Virtual Host nascosti
- **DNS Fuzzing:** Enumera sottodomini

---

## Come usarlo

### Directory fuzzing

```bash
gobuster dir -u http://target.com -w /usr/share/wordlists/dirb/common.txt
```

### VHost fuzzing

```bash
gobuster vhost -u http://target.com -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-110000.txt --append-domain
```

### DNS subdomain fuzzing

```bash
gobuster dns -d target.com -w /usr/share/seclists/Discovery/DNS/subdomains-top1million-5000.txt
```

### Fuzz mode — fuzzing generico con parola chiave `FUZZ`

La modalità `fuzz` sostituisce la keyword **FUZZ** in qualsiasi parte della richiesta (URL, header, body) con ogni parola della wordlist. A differenza di `dir` (che fuzza solo il path), `fuzz` permette di iniettare la wordlist ovunque: parametri, JSON body, header custom, ecc.

```bash
# Fuzzing di un parametro in un JSON body (es. enumerazione email)
gobuster fuzz \
  -u http://target.com/api/v1/account/forgot-password \
  -H "Content-Type: application/json" \
  -m POST \
  -B '{"user":{"email":"FUZZ@target.com"}}' \
  -w /usr/share/seclists/Usernames/xato-net-10-million-usernames.txt \
  -b 404,400,500
```

| Flag | Significato |
|------|-------------|
| `-u` | URL target — può contenere `FUZZ` nel path o nei parametri |
| `-H` | Header HTTP custom (ripetibile) |
| `-m` | Metodo HTTP (`GET`, `POST`, `PUT`, …) |
| `-B` | Body della richiesta — `FUZZ` viene sostituito con ogni parola |
| `-w` | Wordlist |
| `-b` | Status code da escludere (blacklist) |
| `-fw` | Filtra per numero di parole nella risposta |
| `-fl` | Filtra per numero di righe nella risposta |
| `-fs` | Filtra per dimensione della risposta in byte |

La keyword `FUZZ` può comparire in più posizioni contemporaneamente (URL + body + header) e viene sostituita ovunque con la stessa parola ad ogni tentativo.

---

### Opzioni utili

- `-t 50` — Numero di thread (più veloce)
- `-k` — Ignora errori certificati SSL
- `-o risultati.txt` — Salva output in file
- `-x php,html,txt` — Cerca file con queste estensioni

> Fonte: https://github.com/OJ/gobuster
