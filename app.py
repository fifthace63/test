from datetime import date, datetime
from typing import List, Dict
from flask import Flask, render_template, request, redirect, url_for, flash

import db

app = Flask(__name__)
app.secret_key = "change-me"

SLOTS: List[Dict[str, str]] = [
    {"id": "fasting", "label": "ناشتا"},
    {"id": "after_breakfast", "label": "بعد از صبحانه"},
    {"id": "after_morning_snack", "label": "بعد از میان‌وعده صبح"},
    {"id": "before_lunch", "label": "قبل از ناهار"},
    {"id": "after_lunch", "label": "بعد از ناهار"},
    {"id": "pre_workout", "label": "قبل از تمرین"},
    {"id": "intra_workout", "label": "حین تمرین"},
    {"id": "post_workout", "label": "بعد از تمرین"},
    {"id": "before_dinner", "label": "قبل از شام"},
    {"id": "after_dinner", "label": "بعد از شام"},
    {"id": "bedtime", "label": "زمان خواب"},
]


@app.before_first_request
def _init_db() -> None:
    db.init_db()


def _today_str() -> str:
    return date.today().isoformat()


@app.get("/")
def daily_view():
    today_str = _today_str()
    meds = db.list_meds()

    # Build schedule per slot
    schedule = []
    for slot in SLOTS:
        due_items = []
        for med in meds:
            if slot["id"] not in med["slots"]:
                continue
            if not db.is_med_due_today(med, date.today()):
                continue
            taken = db.get_intake(med["id"], today_str, slot["id"])  # None or dict
            due_items.append({
                "med": med,
                "taken": taken,
            })
        schedule.append({
            "slot": slot,
            "items": due_items,
        })

    return render_template("index.html", schedule=schedule, today=today_str)


@app.post("/intake")
def record_intake():
    med_id = int(request.form["med_id"])
    slot_id = request.form["slot_id"]
    today_str = _today_str()
    db.record_intake(med_id, today_str, slot_id)
    flash("ثبت شد.", "success")
    return redirect(url_for("daily_view"))


@app.post("/undo-intake")
def undo_intake():
    med_id = int(request.form["med_id"])
    slot_id = request.form["slot_id"]
    today_str = _today_str()
    db.delete_intake(med_id, today_str, slot_id)
    flash("حذف شد.", "info")
    return redirect(url_for("daily_view"))


@app.get("/meds")
def meds_list():
    all_meds = db.list_meds()
    return render_template("meds.html", meds=all_meds, slots=SLOTS)


@app.get("/meds/new")
def new_med_form():
    return render_template("edit_med.html", med=None, slots=SLOTS, today=_today_str())


@app.post("/meds/new")
def create_med():
    name = request.form["name"].strip()
    dosage = request.form.get("dosage", "").strip()
    notes = request.form.get("notes", "").strip()
    frequency = request.form.get("frequency", "daily")
    start_date = request.form.get("start_date") or _today_str()
    selected_slots = request.form.getlist("slots")

    if not name:
        flash("نام دارو الزامی است.", "error")
        return redirect(url_for("new_med_form"))

    db.add_med(name=name, dosage=dosage, notes=notes, frequency=frequency, start_date=start_date, slots=selected_slots)
    flash("افزوده شد.", "success")
    return redirect(url_for("meds_list"))


@app.get("/meds/<int:med_id>/edit")
def edit_med_form(med_id: int):
    med = db.get_med(med_id)
    if not med:
        flash("پیدا نشد.", "error")
        return redirect(url_for("meds_list"))
    return render_template("edit_med.html", med=med, slots=SLOTS, today=_today_str())


@app.post("/meds/<int:med_id>/edit")
def update_med(med_id: int):
    name = request.form["name"].strip()
    dosage = request.form.get("dosage", "").strip()
    notes = request.form.get("notes", "").strip()
    frequency = request.form.get("frequency", "daily")
    start_date = request.form.get("start_date") or _today_str()
    selected_slots = request.form.getlist("slots")

    if not name:
        flash("نام دارو الزامی است.", "error")
        return redirect(url_for("edit_med_form", med_id=med_id))

    db.update_med(med_id=med_id, name=name, dosage=dosage, notes=notes, frequency=frequency, start_date=start_date, slots=selected_slots)
    flash("بروزرسانی شد.", "success")
    return redirect(url_for("meds_list"))


@app.post("/meds/<int:med_id>/delete")
def delete_med(med_id: int):
    db.delete_med(med_id)
    flash("حذف شد.", "info")
    return redirect(url_for("meds_list"))


if __name__ == "__main__":
    db.init_db()
    app.run(host="0.0.0.0", port=5000, debug=True)