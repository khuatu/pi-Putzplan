Nutzungsanleitung – von der Registrierung bis zum Haken
Ich führe dich einmal komplett durch den Ablauf, als wärst du Mitbewohner:in.

a) App öffnen
Auf deinem Handy oder PC Browser öffnen und http://192.168.178.40:8000 aufrufen. Du siehst die Anmeldeseite.

b) Registrieren
Gib einen Benutzernamen (z. B. anna) und ein Passwort ein, klicke „Einloggen / Registrieren“. Wenn der Name noch nicht existiert, wirst du automatisch registriert und eingeloggt. Das Token wird im Hintergrund gespeichert, du siehst nun die Hauptansicht.

c) Ersten Haushalt anlegen
Klicke auf „Neuen Haushalt erstellen“. Im aktuellen Beispiel wird ein Haushalt mit dir (automatisch hinzugefügt) und einem weiteren Mitglied (Paul) sowie zwei Putzplänen (Bad, Küche) erstellt. Du siehst die ID des Haushalts und die erste Zuteilung.

d) Echtzeit aktivieren
Klicke auf „WebSocket verbinden“. Jetzt siehst du live, wenn andere die Seite öffnen oder Änderungen eintreten.

e) Aufgaben erledigen
In der Zuteilung erscheint für jeden Benutzer eine Liste von Aufgaben (z. B. bad|0, kueche|0). Hinter jeder Aufgabe gibt es einen „Erledigt“‑Button. Wenn du deine Aufgabe gemacht hast, klickst du ihn. Der Eintrag wird in der Historie gespeichert.

f) Veto einlegen (optional)
Bist du unzufrieden mit deiner Zuteilung, klicke „Veto“. Das legt ein Veto für deinen Benutzer ein. Alle anderen müssen nun zustimmen. Auf deren Bildschirm erscheint ein Abschnitt mit offenen Vetos und einem „Zustimmen“‑Button. Sobald alle zugestimmt haben, wird der Putzplan neu gemischt.

g) Wiederholung
Jede Woche (oder nach manuellem Anstoßen über den assign‑Endpunkt) wird eine neue Zuteilung erstellt. Die Historie sorgt dafür, dass niemand dauerhaft dieselben Räume putzt.