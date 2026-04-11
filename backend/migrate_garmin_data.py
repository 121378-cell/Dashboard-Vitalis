import sqlite3
import json
import os


def migrate_garmin_data():
    # Cargar datos exportados
    with open("garmin_export.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Conectar a BD de producción
    db_path = os.environ.get("DATABASE_PATH", "/data/app.db")
    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    user_id = "default_user"
    inserted_bio = 0
    inserted_work = 0

    print(
        f"Iniciando migración de {len(data['biometrics'])} biométricas y {len(data['workouts'])} entrenamientos..."
    )

    # Insertar biométricas
    for i, bio in enumerate(data["biometrics"]):
        c.execute(
            "SELECT id FROM biometrics WHERE user_id = ? AND date = ?",
            (user_id, bio["date"]),
        )
        if c.fetchone() is None:
            c.execute(
                """
                INSERT INTO biometrics (user_id, date, data, source, recovery_time, training_status, hrv_status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    bio["date"],
                    bio["data"],
                    bio["source"],
                    bio["recovery_time"],
                    bio["training_status"],
                    bio["hrv_status"],
                ),
            )
            inserted_bio += 1

        if i % 100 == 0:
            print(f"Procesadas {i}/{len(data['biometrics'])} biométricas...")

    # Insertar entrenamientos
    for i, workout in enumerate(data["workouts"]):
        c.execute(
            'SELECT id FROM workouts WHERE source = "garmin" AND external_id = ?',
            (workout["external_id"],),
        )
        if c.fetchone() is None:
            c.execute(
                """
                INSERT INTO workouts (user_id, source, external_id, name, description, date, duration, calories)
                VALUES (?, 'garmin', ?, ?, ?, ?, ?, ?)
            """,
                (
                    user_id,
                    workout["external_id"],
                    workout["name"],
                    workout["description"],
                    workout["date"],
                    workout["duration"],
                    workout["calories"],
                ),
            )
            inserted_work += 1

        if i % 100 == 0:
            print(f"Procesados {i}/{len(data['workouts'])} entrenamientos...")

    conn.commit()
    conn.close()

    print("\n✅ Migración completada exitosamente:")
    print(f"   - {inserted_bio} registros biométricos nuevos insertados")
    print(f"   - {inserted_work} entrenamientos nuevos insertados")
    print(
        f"   - Saltados {len(data['biometrics']) - inserted_bio} biométricas ya existentes"
    )
    print(
        f"   - Saltados {len(data['workouts']) - inserted_work} entrenamientos ya existentes"
    )


if __name__ == "__main__":
    migrate_garmin_data()
