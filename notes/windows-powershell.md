# Comandi Facili Windows — PowerShell + Equivalenti Linux

I cmdlet PowerShell seguono la struttura **Verbo-Sostantivo** (es. `Get-Process`).
Non è case-sensitive. Usa **Tab** per l'autocompletamento.

---

## Aiuto e Ricerca

| Windows (PowerShell) | Linux | Descrizione |
|---|---|---|
| `Get-Help <cmd>` | `man <cmd>` | Mostra il manuale di un comando |
| `Get-Help <cmd> -Online` | `man <cmd>` / web | Apre la doc online Microsoft |
| `Get-Command *keyword*` | `apropos keyword` | Cerca comandi per nome/parola chiave |
| `Get-Member` | — | Mostra proprietà e metodi di un oggetto |

---

## File e Cartelle

| Windows (PowerShell) | Linux | Descrizione |
|---|---|---|
| `Get-Location` / `pwd` | `pwd` | Directory corrente |
| `Set-Location <path>` / `cd` | `cd <path>` | Cambia directory |
| `Get-ChildItem` / `ls` / `dir` | `ls -la` | Elenca file e cartelle |
| `New-Item -ItemType File <nome>` | `touch <nome>` | Crea un file |
| `New-Item -ItemType Directory <nome>` | `mkdir <nome>` | Crea una cartella |
| `Remove-Item <nome>` / `rm` | `rm <nome>` | Elimina file/cartella |
| `Copy-Item <src> <dst>` | `cp <src> <dst>` | Copia |
| `Move-Item <src> <dst>` | `mv <src> <dst>` | Sposta/rinomina |
| `Get-Content <file>` / `cat` | `cat <file>` | Legge il contenuto di un file |
| `Set-Content <file> "testo"` | `echo "testo" > file` | Scrive in un file |

---

## Processi e Servizi

| Windows (PowerShell) | Linux | Descrizione |
|---|---|---|
| `Get-Process` | `ps aux` | Elenca processi attivi |
| `Stop-Process -Name <nome>` | `pkill <nome>` | Termina un processo per nome |
| `Stop-Process -Id <pid>` | `kill <pid>` | Termina un processo per PID |
| `Get-Service` | `systemctl list-units` | Stato di tutti i servizi |
| `Start-Service <nome>` | `systemctl start <nome>` | Avvia un servizio |
| `Stop-Service <nome>` | `systemctl stop <nome>` | Ferma un servizio |
| `Restart-Service <nome>` | `systemctl restart <nome>` | Riavvia un servizio |

---

## Rete e Diagnostica

| Windows (PowerShell) | Linux | Descrizione |
|---|---|---|
| `Get-NetIPAddress` | `ip a` | Mostra indirizzo IP |
| `Test-Connection <host>` | `ping <host>` | Ping verso un host |
| `Resolve-DnsName <host>` | `dig <host>` / `nslookup` | Risoluzione DNS |
| `Test-NetConnection <host> -Port <n>` | `nc -zv <host> <port>` | Testa una porta specifica |
| `Get-NetTCPConnection` | `ss -tulnp` / `netstat -tulnp` | Connessioni attive |

---

## Pipeline (`|`)

La pipeline passa l'output di un comando come input al successivo — stesso concetto su entrambi i sistemi.

| Windows (PowerShell) | Linux | Descrizione |
|---|---|---|
| `Where-Object { $_.Prop -eq "val" }` | `grep` / `awk` | Filtra risultati |
| `Select-Object Name, Id` | `cut` / `awk '{print $1}'` | Seleziona colonne |
| `Sort-Object <prop>` | `sort` | Ordina risultati |
| `Measure-Object` | `wc` | Conta elementi |
| `Out-GridView` | — | Apre risultati in finestra grafica |
| `Export-Csv <file>` | `> file.csv` | Esporta in CSV |

**Esempi rapidi:**

```powershell
# Processi che usano più CPU
Get-Process | Where-Object {$_.CPU -gt 10} | Sort-Object CPU -Descending

# Equivalente Linux
ps aux --sort=-%cpu | awk '$3 > 1.0'
```

```powershell
# Servizi in esecuzione
Get-Service | Where-Object {$_.Status -eq "Running"} | Select-Object Name, DisplayName

# Equivalente Linux
systemctl list-units --type=service --state=running
```
