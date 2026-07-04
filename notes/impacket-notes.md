# Impacket — Note

**Impacket** è una potente libreria open-source scritta in Python, progettata per creare, manipolare e decodificare pacchetti di rete a basso livello. Sviluppata da Fortra's Core Security, è lo strumento di riferimento per interagire in remoto con i protocolli di rete di Windows.

## Installazione

```bash
pip3 install impacket
```

## Script principali

| Script | Uso |
|--------|-----|
| `mssqlclient.py` | Connessione a Microsoft SQL Server |
| `wmiexec.py` | Esecuzione comandi remoti via WMI |
| `samrdump.py` | Enumerazione utenti SAM via RPC |
| `smbclient.py` | Client SMB interattivo |
| `secretsdump.py` | Dump credenziali (SAM, LSA, NTDS) |
| `psexec.py` | Shell remota stile PsExec |

## Esempi d'uso

```bash
# Connessione MSSQL con auth Windows
python3 mssqlclient.py Administrator@10.129.201.248 -windows-auth

# Enumerazione utenti
samrdump.py 10.129.14.128

# Esecuzione comandi via WMI
/usr/share/doc/python3-impacket/examples/wmiexec.py Cry0l1t3:"P455w0rD!"@10.129.201.248 "hostname"
```
