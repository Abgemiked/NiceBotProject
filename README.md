# NiceBot

NiceBot is an allinclusive Discordbot(Python)   

## Channel
```
Temporary voice channel -> serves as access to the temporary voice channel

Statistics channel      -> shows members without bots
```
## Filter
```
Spamchannel     -> deletes everything except a certain word

GIF channel     -> deletes everything except GIFs

Picture channel -> deletes everything except pictures & replies to pictures

Bot commands    -> deletes everything except "/" commands
```
`
If a message is deleted by a filter, the sender receives a DM with the explanation:
"Your message from "Abgemiked's Gang -> oof" has been deleted, please do not send messages there. 
The channel is only for the word "oof"." (An example of the "oof channel")
`

## Commands
```
/wetter           -> shows you the weather for the location of your choice
/rang             -> shows your current level with experience points
/rangliste        -> shows the 20 highest members depending on their level
/limit            -> number sets the user limit of the current voice channel to the desired number
/hilfe            -> will redirect to an overview in the future
/serverstats      -> shows you the total number of members and the number without bots
/einstellungen    -> Adjust values in config.json
/löschen          -> deletes an amount of messages
/rang_geben       -> gives a lvl to an user
/streamer         -> Creating a category, based on a template, for a specific user
/streamer_löschen -> Deletes a category of a streamer
```
`
Some of the commands needs one or more specific value to use it
`
## Setup

```
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # Windows
cp config.example.json config.json              # Werte eintragen
python main.py
```

Konfiguration: Umgebungsvariablen (`NICEBOT_<KEY>` oder `<KEY>`, z.B. `NICEBOT_TOKEN`)
überschreiben die Werte aus `config.json`. Eine `.env`-Datei wird automatisch geladen
(python-dotenv). Der Pfad zur Level-Datenbank ist über `DB_PATH` konfigurierbar
(Default: `./level_system.db`), der Pfad zur Config über `CONFIG_PATH`.

## Support

This bot is not distributed, so support is available rather sporadically. 
However, please open an issue if you notice a bug.

## License

GNU General Public License v3.0
