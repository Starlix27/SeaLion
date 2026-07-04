# SSH — Note Operative

## Chiavi SSH

- Se abbiamo accesso di scrittura alla directory `.ssh` possiamo leggere le chiavi private:
  - `/home/user/.ssh/id_rsa`
  - `/root/.ssh/id_rsa`

### Usare una chiave rubata

Se possiamo leggere `/root/.ssh/id_rsa`:

```bash
# Copiare la chiave sulla nostra macchina
# Impostare permessi restrittivi (necessario per SSH)
chmod 600 id_rsa

# Connettersi
ssh root@10.10.10.10 -i id_rsa
```

### Persistenza tramite authorized_keys

Se hai accesso alla cartella `.ssh` di un utente, puoi aggiungere la **tua** chiave pubblica nel file `/home/user/.ssh/authorized_keys`. Da quel momento potrai entrare nel server via SSH ogni volta che vorrai.

---

## Cracking Password SSH

### Cercare chiavi private nel filesystem

Le chiavi SSH non hanno estensioni specifiche. Spesso sono delimitate tra `-----BEGIN` e `PRIVATE KEY-----`.

```bash
# Ricerca ricorsiva nel filesystem
grep -rnE '^\-{5}BEGIN [A-Z0-9]+ PRIVATE KEY\-{5}$' /* 2>/dev/null
```

### Verificare se una chiave è cifrata

```bash
ssh-keygen -yf ~/.ssh/id_ed25519
# Se mostra ssh-ed25519... = no password
# Se chiede passphrase = cifrata
```

### Crackare una chiave cifrata

```bash
# Estrarre hash
ssh2john.py SSH.private > ssh.hash

# Crack con wordlist
john --wordlist=rockyou.txt ssh.hash

# Vedere risultato
john ssh.hash --show
```
