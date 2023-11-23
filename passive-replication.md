# Passive Replication

## Genereller Ablauf

- Client schickt Request an Server
  - bei GET-Request: Primary kann Anfrage direkt beantworten
  - bei POST-Request: Primary leitet Anfrage an alle Backups weiter. Erst wenn diese Antworten kriegt der Client seine Bestätigung.

### Anmeldung

- Client registriert sich per POST an `client/init`
- Client authentifiziert sich per POST an `client/auth` mit Nutzername und Passwort
- Client kann nun Daten synchronisieren etc.
- Alle Server kennen nun die Adresse des Clients

### Registrierung eines neuen Backups

- Backup kontaktiert Primary unter `replication/init-backup`
- Primary fügt Backup zu seiner Liste aller verfügbarer Backups hinzu
- Primary antwortet mit Liste aller anderen Backups
- Backup kontaktiert alle anderen Backups unter `replication/set-backups` und teilt neue Liste aller Backups mit

### Primary fällt aus

- Ein Client schickt eine Anfrage. Diese kann nicht zugestellt werden, da der Server ausgefallen ist.
  - Der Client muss die Anfrage jetzt so lange wiederholen, bis er eine Antwort erhält
- Ein Backup stellt fest, dass der Primary ausgefallen ist
- Die Backups kontaktieren sich untereinander und wählen einen neuen Primary (z.B. Bully-Algorithmus)
- Der neue Primary kontaktiert alle Clients und teilt ihnen mit, dass er der neue Primary ist
- Der nächste Zustellungsversuch des Clients ist jetzt erfolgreich

### Backup fällt aus

- Primary schickt routinemäßig eine Anfrage an ein Backup
- Timeout der Anfrage
- Primary entfernt dieses Backup aus Liste aller verfügbaren Backups
- aktualisierte Liste wird den Backups mitgeteilt


## Endpoints

All messages contain a parameter that indicates the original source of the message:
- `client=<Address>`: The message was forwarded by the server, the original sender is the `client`.
- `port=<int>`: The message was sent directly by the client.

### Server

| Path                      | Parameters             | Purpose                                                                               |
|---------------------------|------------------------|---------------------------------------------------------------------------------------|
| `client/init`             |                        | Register a new client                                                                 |
| `client/auth`             | `username`, `password` | Authenticate the client                                                               |
| `client/demo-message`     | `message`              | Print the message on all servers. Used for demonstrating how messages are replicated. |
| `replication/init-backup` |                        | Inform the primary that the sender is a new backup server                             |
| `replication/set-backups` | `backups`              | Inform a backup server about all other backup servers                                 |
