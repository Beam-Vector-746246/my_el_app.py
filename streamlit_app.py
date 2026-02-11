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

    # 1. Hent Spotpriser (API henter 15-min eller 60-min data)
    filter_json = '{"PriceArea":["' + BZN + '"]}'
    spot_url = f"https://api.energidataservice.dk/dataset/DayAheadPrices?filter={urllib.parse.quote(filter_json)}&limit=200"

    try:
        res = requests.get(spot_url).json().get('records', [])
        
        # --- 2026 KONSTANTER (Alle priser herunder er EKSKL. MOMS) ---
        MOMS = 1.25
        AFGIFT = 0.008        # Lovpligtig elafgift 2026 (EU minimum)
        SYSTEM_TARIF = 0.115  # Energinet System/Transmissions-tarif 2026
        HANDEL = 0.050        # Estimeret tillæg til din udbyder (spot-tillæg)
        
        behandlet = []
        for r in res:
            dt = datetime.fromisoformat(r['TimeDK'].replace('Z', ''))
            
            # Vi viser kun priser fra nu og frem
            if dt < nu.replace(minute=0, second=0, microsecond=0): 
                continue
            
            h = dt.hour
            
            # --- N1 VINTER-TARIF 2026 (Transport - Ekskl. Moms) ---
            # N1's priser er ca. 0,99 / 0,33 / 0,11 INKL. moms. 
            # Herunder er de omregnet til EKSKL. moms for korrekt matematik:
            if 17 <= h < 21:    
                tarif = 0.791  # Spidslast (Vinter)
            elif 0 <= h < 6:    
                tarif = 0.088  # Lavlast (Nat)
            else:               
                tarif = 0.264  # Højlast (Dag/Aften)
            
            # --- SAMLET BEREGNING ---
            # Vi summerer alt det "rå" beløb og ganger med 1.25 til sidst
            spot_kwh = r['DayAheadPriceDKK'] / 1000
            alt_ekskl_moms = spot_kwh + tarif + SYSTEM_TARIF + AFGIFT + HANDEL
            total_pris = round(alt_ekskl_moms * MOMS, 2)
            
            behandlet.append({'tid': dt, 'pris': total_pris})
        
        behandlet.sort(key=lambda x: x['tid'])

        if behandlet:
            p_vis = behandlet[:96] 
            x = [d['tid'] for d in p_vis]
            y = [d['pris'] for d in p_vis]
            gns_pris = sum(y) / len(y)

            # --- DISPLAY METRICS ---
            col1, col2 = st.columns(2)
            pris_nu = behandlet[0]['pris']
            col1.metric("Pris nu", f"{pris_nu:.2f} kr")
            col2.metric("Snit (24t)", f"{gns_pris:.2f} kr")

            # --- VISUALISERING ---
            fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
            plt.style.use('bmh')

            # Farver: Rød hvis > 10% over snit, grøn hvis < 10% under snit
            farver = ['#e74c3c' if v > gns_pris * 1.10 else ('#2ecc71' if v < gns_pris * 0.90 else '#f1c40f') for v in y]
            
            ax1.bar(x, y, color=farver, width=0.008)
            ax1.axhline(gns_pris, color='black', linestyle='--', alpha=0.6)

            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            ax1.set_ylabel("Total kr/kWh (inkl. moms/afgift)")
            
            # Timetal over søjlerne (for hver hele time)
            for i in range(0, len(x), 4 if len(x) > 40 else 1): 
                ax1.text(x[i], y[i] + 0.02, f"{y[i]:.2f}", 
                         ha='center', fontsize=7, weight='bold')

            st.pyplot(fig)
            
            st.info(f"""
            **Beregning for kl. {behandlet[0]['tid'].strftime('%H:%M')}:**
            - Spotpris (inkl. moms): {round((behandlet[0]['pris']/MOMS - (tarif + SYSTEM_TARIF + AFGIFT + HANDEL))*MOMS, 2)} kr.
            - Tariffer & Afgifter (inkl. moms): {round((tarif + SYSTEM_TARIF + AFGIFT + HANDEL)*MOMS, 2)} kr.
            """)
            
    except Exception as e:
        st.error(f"Fejl: {e}")

if __name__ == "__main__":
    hent_silkeborg_analyse()
