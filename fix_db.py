import sqlite3
import traceback
from app import time_to_sec, calculate_fina_points, DB_SQLITE_PATH

print("🔄 Начинаю умный перерасчет базы данных...")

def guess_gender_smart(fullname):
    parts = fullname.strip().split()
    if len(parts) < 2: return "М"
    
    surname = parts[0].lower()
    fname = parts[1].lower()

    if surname.endswith(('ов', 'ев', 'ёв', 'ин', 'ский', 'ый')):
        return "М"
    if surname.endswith(('ова', 'ева', 'ёва', 'ина', 'ская', 'ая')):
        return "Ж"

    male_exceptions = ['илья', 'никита', 'данила', 'савва', 'лука', 'кузьма', 'добрыня', 'лев']
    if fname in male_exceptions:
        return "М"

    if fname.endswith('а') or fname.endswith('я'):
        return "Ж"
        
    return "М"

try:
    conn = sqlite3.connect(DB_SQLITE_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT rowid, РЕЗУЛЬТАТ, ДИСТАНЦИЯ, БАССЕЙН, СПОРТСМЕН FROM results")
    rows = cursor.fetchall()

    fixed_count = 0

    for row in rows:
        rowid = row[0]
        result_str = str(row[1]).strip()
        dist = str(row[2]).strip()
        pool = str(row[3]).strip()
        athlete = str(row[4]).strip()

        clean_result_str = result_str
        if clean_result_str.count('.') == 2:
            clean_result_str = clean_result_str.replace('.', ':', 1)

        if "1500" in dist and "В/С" not in dist.upper() and "КРОЛЬ" not in dist.upper():
            dist = "1500 в/с"
        
        new_sec = time_to_sec(clean_result_str)
        guessed_gender = guess_gender_smart(athlete)
        new_pts = calculate_fina_points(new_sec, dist, pool, explicit_gender=guessed_gender)
        
        cursor.execute(
            "UPDATE results SET РЕЗУЛЬТАТ = ?, ДИСТАНЦИЯ = ?, СЕКУНДЫ = ?, ОЧКИ = ? WHERE rowid = ?", 
            (clean_result_str, dist, new_sec, new_pts, rowid)
        )
        fixed_count += 1

    conn.commit()
    conn.close()

    print(f"✅ Успешно! Исправлено {fixed_count} записей.")
    print("Теперь Илья и Никита снова стали мужчинами, а стайерам начислены очки!")

except Exception as e:
    print("❌ Ошибка:")
    traceback.print_exc()