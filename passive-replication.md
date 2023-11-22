# DS shit

Ziel: Passive replication

- Primary muss alle Änderungen an Backups weiterleiten

## Szenarien

### Anmeldung

- Client kontaktiert Primary und baut Verbindung auf
- Primary teilt IP des Clients an alle Backups mit
- Client schickt credentials
- Primary informiert Backups über Status der Anmeldung

### Failure im Primary

#### Konzept

- Backup stellt fest dass Primary ausgefallen ist
- neuer Primary muss irgendwie gewählt werden
- Clients und Backups müssen über neuen Primary informiert werden

#### Ablauf

- Ausfall feststellen: Heartbeat zwischen Primary und Backups?
- neuen Primary wählen (dafür gibt es Algorithmen)
- neuer Primary informiert alle Backups und Clients
	- diese brechen dann die Verbindung zum alten Primary ab und bauen eine neue auf
	- dafür muss der Primary die IPs aller Clients und Backups kennen, diese müssen auch auf neue Meldungen warten

## Umsetzung

### Client

#### Variablen

- **IP/Port** von aktuellem Primary

#### Verbindungen

- als Client: dauerhafte Verbindung zum Primary
- als Server: kleine Schnittstelle über die ein neuer Primary mitgeteilt werden kann

### Server

#### Variablen

- IPs aller anderen Server
- IPs und Login-Status aller Clients
- aktuelle Rolle: Primary / Backup
- 
