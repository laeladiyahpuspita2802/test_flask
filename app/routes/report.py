from flask import Blueprint, render_template, current_app
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from wordcloud import WordCloud
import base64
import io

report_bp = Blueprint('report', __name__, url_prefix='')

@report_bp.route('/reports')
def reports():
    # Ambil data dari MongoDB
    articles = list(current_app.db.article.find())
    df = pd.DataFrame(articles)

    # Validasi awal
    if df.empty or 'tanggal_publish' not in df.columns or 'isi' not in df.columns:
        return render_template('report.html', image1=None, image2=None, image3=None, tabel=[])

    # Preprocessing tanggal
    df['tanggal_publish'] = pd.to_datetime(df['tanggal_publish'], errors='coerce')
    df = df.dropna(subset=['tanggal_publish'])

    # Filter keyword Prolaps Uteri
    keyword = ['prolaps uteri', 'turun peranakan', 'panggul', 'uterine']
    df = df[df['isi'].str.lower().apply(lambda x: any(k in x for k in keyword) if isinstance(x, str) else False)]

    # Hitung jumlah kata
    df['jumlah_kata'] = df['isi'].apply(lambda x: len(x.split()) if isinstance(x, str) else 0)

    # GRAFIK 1: Artikel per Bulan
    df['bulan'] = df['tanggal_publish'].dt.to_period('M').astype(str)
    fig1, ax1 = plt.subplots()
    df.groupby('bulan').size().plot(kind='bar', ax=ax1, color='skyblue')
    ax1.set_title('Artikel tentang Prolaps Uteri per Bulan')
    ax1.set_xlabel('Bulan')
    ax1.set_ylabel('Jumlah')
    plt.xticks(rotation=45)
    plt.tight_layout()
    image1 = fig_to_base64(fig1)

    # GRAFIK 2: Distribusi Panjang Artikel
    sns.set_theme()
    fig2, ax2 = plt.subplots()
    sns.histplot(df['jumlah_kata'], bins=20, kde=True, ax=ax2, color='orange')
    ax2.set_title('Distribusi Panjang Artikel')
    ax2.set_xlabel('Jumlah Kata')
    ax2.set_ylabel('Frekuensi')
    plt.tight_layout()
    image2 = fig_to_base64(fig2)

    # GRAFIK 3: WordCloud
    text = " ".join(df['isi'].dropna().astype(str))
    wordcloud = WordCloud(width=800, height=400, background_color='white').generate(text)
    fig3, ax3 = plt.subplots(figsize=(10, 5))
    ax3.imshow(wordcloud, interpolation='bilinear')
    ax3.axis("off")
    plt.tight_layout()
    image3 = fig_to_base64(fig3)

    # Tabel Artikel Terbaru
    tabel = df.sort_values("tanggal_publish", ascending=False)[["title", "tanggal_publish", "sumber", "link"]].head(5)
    tabel = tabel.fillna("")
    tabel['tanggal_publish'] = tabel['tanggal_publish'].dt.strftime('%Y-%m-%d')

    return render_template('report.html', image1=image1, image2=image2, image3=image3, tabel=tabel.to_dict(orient='records'))


def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    buf.close()
    plt.close(fig)
    return image_base64
