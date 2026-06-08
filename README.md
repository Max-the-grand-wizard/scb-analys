# SCB Anställningsanalys

Ett Python-verktyg som hämtar och analyserar data från SCB:s API om pågående anställningar med en anställningstid på 6 månader eller mindre. Verktyget är paketerat i en Docker-container så att det fungerar på vilken dator som helst utan att installera Python.

## Om projektet

Verktyget hämtar data från SCB:s officiella API för tabellen "Pågående anställningar - anställningstid ≤6 månader". Datan presenteras i en tydlig tabell uppdelad per sektor och kön.

### Vad visar analysen?

- Antal korta anställningar per sektor (Näringslivet, Staten, Region, Kommun, Hushållens organisationer)
- Fördelning mellan män och kvinnor
- Totala antalet korta anställningar för vald månad

## Krav

### För Docker-alternativet:
- Docker Desktop (Windows/Mac) eller Docker Engine (Linux)

### För Python-alternativet:
- Python 3.6 eller senare
- Internetuppkoppling för att hämta data från SCB

## Installation och användning

### Alternativ 1: Köra med Docker (rekommenderas)

1. **Klona eller ladda ner projektet**
   ```bash
   git clone https://github.com/ditt-anvandarnamn/scb-analys.git
   cd scb-analys

# Bygg Docker-imagen
docker build -t scb-analys .

# Kör containern
För att köra med senaste tillgängliga data (mars 2026):

docker run scb-analys

# För att specificera en annan månad:
    docker run scb-analys python scb_analys_final.py 2024M02


# Alternativ 2: Köra direkt med Python
1. Installera beroenden
pip install pandas requests

2. Kör skriptet
python scb_analys_final.py

3. Med specifik månad:
python scb_analys_final.py 2024M02



# Användningsexempel
Exempel 1: Visa data för mars 2026
docker run scb-analys

=== HÄMTAR DATA FÖR Mar 2026 ===

DATA FRAN SCB (Mar 2026):
------------------------------------------------------------
Sektor                                   Män   Kvinnor    Totalt
------------------------------------------------------------
Samtliga sektorer                    517,091   533,771  1,050,863
Näringslivet                         409,950   331,562    741,512
Staten                                22,754    25,660     48,414
Region                                10,217    30,068     40,285
Kommun                                51,138   118,255    169,393
Hushållens organisationer             23,031    28,223     51,254
------------------------------------------------------------

TOTAL: 1,050,863 korta anställningar i Mar 2026