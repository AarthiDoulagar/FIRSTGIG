# FirstGig

Verified micro-freelance platform for students. Flask + SQLite. Mock escrow only — no real payments.

## Run locally

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python seed.py
python app.py
```

Open http://127.0.0.1:5000

## Demo logins (password: `password123`)

| Role | Email | Notes |
| --- | --- | --- |
| Admin | admin@firstgig.test | Disputes, stats, suspend |
| Student | aarthi@college.edu | Verified Freelancer (~7 gigs) |
| Student | rohan@college.edu | FirstGig Beginner |
| Student | priya@college.edu | Active Freelancer |
| Student | kabir@college.edu | Rising Freelancer |
| Student | meera@college.edu | Trusted Freelancer |
| Client | ananya@novalabs.test | Nova Labs |
| Client | vikram@pixelcraft.test | Pixelcraft (open dispute) |
| Client | sana@campushire.test | CampusHire |

## Core demo path

1. Login as Aarthi → marketplace recommendations → apply (already applied to Flask portfolio).
2. Login as Ananya → applicants → Accept → project + Held escrow.
3. Login as student → submit work.
4. Login as client → Approve → Released escrow → both leave reviews → level/reliability update → Add to Portfolio.
5. Overdue path: Rohan's disputed banner project → Admin → Refund Client or Extend Deadline.

College verification is simulated: registering a new student shows a 6-digit demo code.
