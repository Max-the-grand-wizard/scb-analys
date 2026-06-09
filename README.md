# SCB Anställningsanalys - Webbsida

En Flask-baserad webbapplikation som hämtar och visar data från SCB:s API om pågående anställningar med en anställningstid på ≤6 månader.

## Funktioner

- Visa statistik per sektor (Näringslivet, Staten, Region, Kommun m.fl.)
- Fördelning mellan män och kvinnor
- Välj månad via dropdown-meny
- Docker-container för enkel körning

## Installation och användning

### Alternativ 1: Köra med Docker (rekommenderas)

```bash
# Bygg Docker-imagen
docker build -t scb-analys .


# Kör containern
docker run -p 5000:5000 scb-analys


ALTERNATIV 2: Köra direkt med Python

# Installera beroenden
pip install flask pandas requests

# Kör appen
python app.py


TEKNOLOGIER

Flask - Webbramverk

Pandas - Datahantering

Docker - Containerisering

SCB:s API - Datakälla