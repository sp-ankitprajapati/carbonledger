# CarbonLedger update: code ko Hinglish mein samjho

Yeh current upgrade ka guide hai. Old walkthrough historical source explain karta hai. Current README aur tests ko final behavior ka reference samjho.

## 1. Input mode ka real meaning

Structured mode ka matlab JSON mein known quantities/units/categories dena. Yeh mock extraction nahi. Tum 2 MWh doge toh 2000 kWh calculate honge;4 MWh doge toh 4000 kWh. Live mode invoice text se Gemini extraction karta hai, jiske liye credentials aur currently available model name chahiye. Missing key ya malformed extraction ko fixed 450 litre se replace nahi karte.

## 2. Same units par math

app/units.py har known unit ko dimension aur scale se map karta hai. MWh aur kWh same energy dimension hain. kg aur litre alag hain. Density assume karke convert nahi karte. Formula: normalized=quantity*source_scale / target_scale. app/calculator.py normalized quantity*factor karke kgCO2e aur tonnes nikalta hai. Source quantity/unit record mein bachte hain.

Practice: 2 MWh*1000=2000 kWh;2000*.716=1432 kgCO2e=1.432 tonnes.100 litre diesel*2.68=268 kg=.268 tonnes. Combined total 1.7 tonnes. Tiny line items ko round karne se pehle sum karna zaroori hai, warna small contributions disappear ho sakte hain.

## 3. Classifier ka result weak tha toh kya badla?

48 synthetic examples/15 classes, minimum class mein 2 examples. Two-fold CV mein vectorizer har fold ke training data par fit hota hai. MLP 39.58% accuracy, macroF1 .3474. Old 0.55 gate 13 items accept karta hai aur sirf 5 correct hain. Confidence ko correctness probability assume nahi kar sakte.

Default mein model category suggest karta hai, calculation se pehle confirmation chahiye. Item status needs_confirmation hota hai. Check karke activity_key structured input mein resubmit karo. Optional experimental flag automatically suggested categories use karta hai, aur audit mein flag record hota hai. Is mode ko production quality mat bolo.

## 4. Retrieval aur LLM boundary

Retriever TF-IDF / cosine similarity se candidates deta hai. Zero overlap ko supported match nahi maana. Live LLM ko sirf retrieved candidate ya UNMATCHED choose karna allowed hai. Code membership validate karta hai; prompt alone enough nahi. Unknown key, wrong unit aur invalid JSON ko silently calculate nahi karte.

## 5. Durable audit aur PDF

Har run UUID banata hai. JSON mein input hash, mode, original/converted quantities, factor_set, decisions, accepted records aur rejected items save hote hain. Temporary file write hone ke baad final filename replace hota hai. Yeh process interruption ke time half-written final JSON se bachata hai. Local JSON editable hai; tamper-proof blockchain nahi.

PDF same computed totals aur full decision appendix use karta hai. Company name aur descriptions escape hote hain, taaki markup text ko formatting instructions na samjha jaye. Filename UUID se banta hai, company name ke path fragments se nahi. API local path ki jagah download URL deta hai. Streamlit directly shared Python logic call karta hai.

## 6. Tests aur interview follow-ups

29 tests mein old 8 aur new 21 cases hain. MWh/kWh equality, NaN/negative rejection, incompatible units, partial totals, candidate membership, API/PDF download aur actual Streamlit submission verify hote hain. Live extraction/classification tests controlled responses use karte hain; live model quality measure nahi hoti.

Questions: optional ID aur quantity contract mein difference? Dataclass type hint runtime validation hai? Structured JSON ko parse kaise karte? Pydantic TypeAdapter list validate kyun? Confidence 0.55 calibrated kyun nahi? Source unit preserve kyun? UUID filename kyun? Atomic write se kya protect hota? Full audit PDF mein kyun? Factor correctness kaise verify karoge? No API calls demo ko API savings benchmark kyun nahi bolte?

## 7. Khud implement karo

normalize_quantity aur 2 MWh calculation bina copy likho. Monkeypatched fake LLM se candidate-set violation create karo. API response se PDF/audit download karo. Rejected kg-versus-litre item ka total unaffected prove karo. A new independently labeled invoice example add karke train/test contamination ka risk explain karo. Finally 90 seconds mein problem, flow, actual result aur limitations bolo.

For detailed foundations and the original walkthrough, see the companion files. Technology coverage: Python/dataclasses, JSON/Pydantic, NumPy/sklearn, TF-IDF, MLP, cosine retrieval/RAG, provider clients, deterministic math, FastAPI, Streamlit/session state/forms, ReportLab, local persistence, pytest, packaging and GitHub CI. Koi document all interview questions guarantee nahi karta; code trace aur independent change se readiness prove hoti hai.


Detailed reading: [Foundations](FOUNDATIONS_HINGLISH.md), [original walkthrough](ORIGINAL_WALKTHROUGH_HINGLISH.md), [practice code](practice_basics.py).
