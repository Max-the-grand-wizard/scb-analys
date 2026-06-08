"""
SCB ANALYS - Pagaende anstallningar med anstallningstid ≤6 manader
Analyserar data hamtad direkt fran SCB:s API
Anvandning: python scb_analys_final.py [ARGUMENT]
Argument:   YYYYMM t.ex. 2026M03 for mars 2026
            Om inget argument anges anvands 2026M03
"""

import sys
import requests
import pandas as pd

# Funktion for att konvertera M-format till lasbart format
def konvertera_manad(manad_kod):
    """
    Konverterar t.ex. '2024M02' till 'Feb 2024'
    """
    try:
        ar = manad_kod[:4]
        manad_del = manad_kod[5:]  # Tar bort 'M' efter ar
        manad_nummer = int(manad_del)
        
        manader = {
            1: "Jan", 2: "Feb", 3: "Mar",
            4: "Apr", 5: "Maj", 6: "Jun",
            7: "Jul", 8: "Aug", 9: "Sep",
            10: "Okt", 11: "Nov", 12: "Dec"
        }
        
        manad_namn = manader.get(manad_nummer, "???")
        return f"{manad_namn} {ar}"
    except:
        return manad_kod  # Returnera original om konvertering misslyckas

# Las manad fran kommandoraden
if len(sys.argv) > 1:
    manad_kod = sys.argv[1]
else:
    manad_kod = "2026M03"

# Skapa lasbar version av manaden
manad_lasbar = konvertera_manad(manad_kod)

print(f"=== HÄMTAR DATA FÖR {manad_lasbar} ===\n")

url = "https://api.scb.se/OV0104/v1/doris/sv/ssd/START/AM/AM0211/AM0211A/PagaendeAnstAnstTid"

# Fraga som hamtar ALL data for specifik manad
query = {
    "query": [
        {
            "code": "ContentsCode",
            "selection": {
                "filter": "all",
                "values": ["*"]
            }
        },
        {
            "code": "Tid",
            "selection": {
                "filter": "item",
                "values": [manad_kod]
            }
        }
    ],
    "response": {
        "format": "json"
    }
}

# Skicka förfrågan
try:
    response = requests.post(url, json=query, timeout=10)
    response.raise_for_status()
except requests.exceptions.Timeout:
    print("FEL: Anslutningen tog för lång tid. Kontrollera din internetuppkoppling.")
    sys.exit(1)
except requests.exceptions.ConnectionError:
    print("FEL: Kunde inte ansluta till SCB:s API. Kontrollera din internetuppkoppling.")
    sys.exit(1)
except requests.exceptions.HTTPError as e:
    print(f"FEL: HTTP-fel {response.status_code} - {e}")
    sys.exit(1)
except Exception as e:
    print(f"FEL: Något gick fel vid anslutningen: {e}")
    sys.exit(1)

data = response.json()

# Kontrollera om data finns for den angivna manaden
if 'data' not in data or len(data['data']) == 0:
    print(f"FEL: Ingen data hittades för {manad_lasbar}")
    print("Möjliga orsaker:")
    print("  - Månaden/året finns inte i SCB:s databas")
    print("  - Data för denna period är inte tillgänglig än")
    print("  - Formatet ska vara t.ex. 2026M03 (år+M+månad)")
    sys.exit(1)

# Mappning av koder till lasbara namn
sektor_mappning = {
    "010": "Samtliga sektorer",
    "030": "Näringslivet",
    "320": "Staten",
    "409": "Region",
    "410": "Kommun",
    "040": "Hushållens organisationer"
}

kon_mappning = {
    "1": "Män",
    "2": "Kvinnor",
    "1+2": "Totalt"
}

# Samla in data
resultat = []
for item in data['data']:
    sektor_kod = item['key'][0]
    kon_kod = item['key'][1]
    
    # Hoppa över "Totalt" for att undvika dubbelrakning
    if kon_kod == "1+2":
        continue
    
    if len(item['values']) > 2:
        antal_kort = item['values'][2]
        
        try:
            antal = int(antal_kort) if antal_kort and antal_kort.isdigit() else 0
        except (ValueError, TypeError):
            antal = 0
        
        resultat.append({
            'sektor': sektor_mappning.get(sektor_kod, sektor_kod),
            'kon': kon_mappning.get(kon_kod, kon_kod),
            'antal': antal
        })

# Kontrollera att vi har data for alla sektorer
if len(resultat) == 0:
    print(f"FEL: Ingen anvandbar data hittades för {manad_lasbar}")
    sys.exit(1)

df = pd.DataFrame(resultat)

# Visa tabellen
print(f"\nDATA FRAN SCB ({manad_lasbar}):")
print("-" * 60)
print(f"{'Sektor':<35} {'Män':>10} {'Kvinnor':>10} {'Totalt':>10}")
print("-" * 60)

sektor_ordning = ["Samtliga sektorer", "Näringslivet", "Staten", "Region", "Kommun", "Hushållens organisationer"]

for sektor in sektor_ordning:
    man_data = df[(df['sektor'] == sektor) & (df['kon'] == 'Män')]['antal'].values
    kvinna_data = df[(df['sektor'] == sektor) & (df['kon'] == 'Kvinnor')]['antal'].values
    
    man = man_data[0] if len(man_data) > 0 else 0
    kvinna = kvinna_data[0] if len(kvinna_data) > 0 else 0
    total = man + kvinna
    
    # Om bade man och kvinna ar 0, skriv ut ett meddelande
    if man == 0 and kvinna == 0 and sektor != "Samtliga sektorer":
        print(f"{sektor:<35} {'N/A':>10} {'N/A':>10} {'N/A':>10}")
    else:
        print(f"{sektor:<35} {man:>10,} {kvinna:>10,} {total:>10,}")

print("-" * 60)

# Visa totalsumma om "Samtliga sektorer" finns
if "Samtliga sektorer" in df['sektor'].values:
    total_alla = df[df['sektor'] == "Samtliga sektorer"]['antal'].sum()
    print(f"\nTOTAL: {total_alla:,} korta anställningar i {manad_lasbar}")