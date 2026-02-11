import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import urllib.parse
from collections import defaultdict

# Page configuration for mobile view
st.set_page_config(page_title="Elpriser Silkeborg 2026", layout="centered")

def hent_silkeborg_analyse():
    BZN = "DK1"
    nu = datetime.now()
    
    st.title("⚡ Silkeborg El-Rapport")
    st.write(f"Opdateret: {nu.strftime('%d/%m %H:%M')}")

    # 1. Hent Spotpriser (15-min or 1-hour intervals)
    filter_json = '{"PriceArea":["' + BZN + '"]}'
    spot_url = f"https://api.energidataservice.dk/dataset/DayAheadPrices?filter={urllib.parse.quote(filter_json)}&limit=200"

    try:
        res = requests.get(spot_url).json().get('records', [])
        
        # --- 2026 KONSTANTER (Ekskl. Moms) ---
        MOMS = 1.25
        AFGIFT = 0.008        # Lovpligtig elafgift 2026 (EU minimum)
        SYSTEM_TARIF = 0.115  # Energinet System/Transmissions-tarif 2026
        HANDEL = 0.040        # Typisk tillæg til elselskabet (Norlys, Andel etc.)
        
        behandlet = []
        for r in res:
            # Håndter tidsformat fra API
            dt = datetime.fromisoformat(r['TimeDK'].replace('Z', ''))
            
            # Vi viser kun priser fra nu og frem
            if dt < nu.replace(minute=0, second=0, microsecond=0): 
                continue
            
            h = dt.hour
            
            # --- N1 VINTER-TARIF 2026 (Transport) ---
            # Gælder Jan-Mar og Okt-Dec
            if 17 <= h < 21:    
                tarif = 0.9884  # Spidslast (Dyrest)
            elif 0 <= h < 6:    
                tarif = 0.1098  # Lavlast (Billigst)
            else:               
                tarif = 0.3295  # Højlast (Dagstimer)
            
            # Samlet kalkulation pr. kWh
            spot_kwh = r['DayAheadPriceDKK'] / 1000
            total_pris = round((spot_kwh + tarif + SYSTEM_TARIF + AFGIFT + HANDEL) * MOMS, 2)
            
            behandlet.append({'tid': dt, 'pris': total_pris})
        
        behandlet.sort(key=lambda x: x['tid'])

        if behandlet:
            # Vis de næste 24 timer (96 intervaller hvis 15-min data)
            p_vis = behandlet[:96] 
            x = [d['tid'] for d in p_vis]
            y = [d['pris'] for d in p_vis]
            gns_pris = sum(y) / len(y)

            # --- DISPLAY METRICS ---
            col1, col2 = st.columns(2)
            # Find den pris der er tættest på lige nu
            pris_nu = behandlet[0]['pris']
            col1.metric("Pris nu", f"{pris_nu:.2f} kr")
            col2.metric("Snit (24t)", f"{gns_pris:.2f} kr")

            # --- VISUALISERING ---
            fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
            plt.style.use('bmh')

            # Farvekodning: Rød = Dyrere end snit, Grøn = Billigere
            farver = ['#e74c3c' if v > gns_pris * 1.10 else ('#2ecc71' if v < gns_pris * 0.90 else '#f1c40f') for v in y]
            
            ax1.bar(x, y, color=farver, width=0.008)
            ax1.axhline(gns_pris, color='black', linestyle='--', alpha=0.6, label="Gennemsnit")

            # Formatering af x-aksen (tidspunkter)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax1.set_ylabel("Total kr/kWh (inkl. alt)")
            
            # Tilføj timetal over de højeste søjler for overblik
            for i in range(0, len(x), 4): # Label hver hel time
                ax1.text(x[i], y[i] + 0.05, f"{y[i]:.2f}", 
                         ha='center', fontsize=8, weight='bold')

            st.pyplot(fig)
            
            st.info("""
            **Info om beregning (2026):**
            - **Transport (N1):** Varierer (Spids: 0,99 kr / Dag: 0,33 kr / Nat: 0,11 kr) ekskl. moms.
            - **Energinet:** 0,115 kr i systemtarif.
            - **Elafgift:** Sænket til 0,008 kr (EU minimum).
            """)
            
    except Exception as e:
        st.error(f"Fejl under hentning af data: {e}")

if __name__ == "__main__":
    hent_silkeborg_analyse()
