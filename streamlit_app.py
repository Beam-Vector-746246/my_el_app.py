import streamlit as st
import requests
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime
import urllib.parse
from collections import defaultdict

# Page configuration for mobile view
st.set_page_config(page_title="Elpriser Silkeborg", layout="centered")

def hent_silkeborg_analyse():
    BZN = "DK1"
    nu = datetime.now()
    
    st.title("⚡ Silkeborg El-Rapport")
    st.write(f"Opdateret: {nu.strftime('%d/%m %H:%M')}")

    # 1. Hent Spotpriser
    filter_json = '{"PriceArea":["' + BZN + '"]}'
    spot_url = f"https://api.energidataservice.dk/dataset/DayAheadPrices?filter={urllib.parse.quote(filter_json)}&limit=300"

    try:
        res = requests.get(spot_url).json().get('records', [])
        
        MOMS = 1.25
        AFGIFT = 0.008 
        
        behandlet = []
        for r in res:
            dt = datetime.fromisoformat(r['TimeDK'].replace('Z', ''))
            if dt < nu.replace(minute=0, second=0, microsecond=0): continue
            
            h = dt.hour
            # N1 Vinter-tariffer 2026
            if 17 <= h < 21:    tarif = 0.99
            elif 0 <= h < 6:    tarif = 0.11
            else:               tarif = 0.33
            
            pris = round(((r['DayAheadPriceDKK'] / 1000) + tarif + AFGIFT) * MOMS, 2)
            behandlet.append({'tid': dt, 'pris': pris})
        
        behandlet.sort(key=lambda x: x['tid'])

        if behandlet:
            p_24 = behandlet[:96]
            x, y = [d['tid'] for d in p_24], [d['pris'] for d in p_24]
            gns_pris = sum(y) / len(y)

            # Display Metrics for quick reading on phone
            col1, col2 = st.columns(2)
            col1.metric("Pris nu", f"{behandlet[0]['pris']:.2f} kr")
            col2.metric("Snit (24t)", f"{gns_pris:.2f} kr")

            # --- VISUALISERING ---
            fig, ax1 = plt.subplots(1, 1, figsize=(10, 6))
            plt.style.use('bmh')

            farver = ['#e74c3c' if v > gns_pris * 1.15 else ('#2ecc71' if v < gns_pris * 0.85 else '#f1c40f') for v in y]
            ax1.bar(x, y, color=farver, width=0.008)
            ax1.axhline(gns_pris, color='black', linestyle='--', alpha=0.6)

            # Timelige gennemsnit labels
            time_grupper = defaultdict(list)
            for d in p_24:
                time_grupper[d['tid'].hour].append((d['tid'], d['pris']))
            
            for time, punkter in time_grupper.items():
                center_tid = punkter[1][0]
                time_gns = sum(p[1] for p in punkter) / len(punkter)
                ax1.text(center_tid, max(y) * 1.02, f"{time_gns:.2f}", 
                        ha='center', fontsize=7, weight='bold',
                        bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

            ax1.set_ylabel("kr/kWh (inkl. moms/tarif)")
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
            st.pyplot(fig)
            
    except Exception as e:
        st.error(f"Fejl under hentning af data: {e}")

if __name__ == "__main__":
    hent_silkeborg_analyse()
