> Historical source walkthrough. Current behavior, numbers and fixes: README.md and LEARNING_HINGLISH.md.

# CarbonLedger: zero se code aur interview tak

Pehle `00` ka Lesson 1 karo. Naye terms ke liye `01_SKILLS_ZERO_SE.md` kholo. Actual source ke liye `06_CARBONLEDGER_CODE_REFERENCE.md` hai. Neeche snippets inspected source se hain. Kuch snippets larger function ka sirf relevant part hain; learning examples separately labeled hain.

## 1. User ki problem kya thi?

Socho ek company ke paas alag vendors ke bills hain: diesel, electricity, freight aur cotton. Har bill ki wording different hai. Company ko estimate chahiye ki activities se kitni greenhouse-gas emissions associated hain.

Raw text:

```text
Generator diesel purchase: 100 litres
Factory electricity: 1,000 kWh
```

Desired structured output roughly:

```json
{
  "scope_1_tco2e": 0.268,
  "scope_2_tco2e": 0.716,
  "scope_3_tco2e": 0,
  "total_tco2e": 0.984
}
```

Yeh calculation example demo factors se hai. Actual live pipeline mein correct extraction/classification bhi honi chahiye. Bina API key wala mock input ko genuinely read nahi karta.

## 2. Domain words pehle samjho

| Term | Easy meaning | Project example |
|---|---|---|
| Activity | Business ne kya use/perform kiya | Diesel burn hua, electricity consume hui |
| Activity data | Us activity ki quantity | 100 litres, 1,000 kWh |
| Emission factor | Har unit activity ka emissions multiplier | 2.68 kg CO2e per litre diesel, demo value |
| CO2e | Climate effect express karne ka common equivalent unit | Factor already kg CO2e per unit deta hai |
| Scope 1 | Owned/controlled sources ki direct emissions | Apne generator mein diesel combustion |
| Scope 2 | Purchased electricity/heat/steam ki indirect emissions | Grid electricity consumption |
| Scope 3 | Baaki value-chain indirect emissions | Supplier goods aur outsourced freight examples |
| Reporting period | Kis duration ka report hai | Q1 2026 |
| Audit trail | Decision/result tak pahunchne ki records | Category NN ne choose ki ya LLM ne |

Scope sirf bill ke keyword se universally decide nahi hota. Ownership/control aur reporting boundary matter karte hain. Current prototype static activity keys ke through scopes assign karta hai.

ESRS/CSRD terms project ki reporting context mein hain. Abhi interview mein itna bolo: "Prototype ESRS E1-style report structure use karta hai." Complete compliance/certification claim mat karo. Repo khud demonstration limitations batata hai.

## 3. Architecture ka complete flow

```text
User invoice text deta hai
  1. Parser: structured line items
  2. Local classifier: category + confidence
  3. Confidence low? Retrieval + Gemini selection
  4. Calculator: quantity × stored factor
  5. Result: summary + classification audit list + unmatched items
  6. Optional: narrative + PDF
```

Remote LLM operations alag hain: extraction, uncertain classification escalation, narrative. Har item ko direct LLM classification dena avoid ho sakta hai, lekin extraction/narrative calls phir bhi ho sakti hain.

## 4. Kaunsi file kya karti hai?

| File | Kaam | Kab padho |
|---|---|---|
| app/emission_factors.py | Demo factors, units, scopes aur lookup helpers | Sabse pehle |
| app/calculator.py | Records aur deterministic arithmetic | Sabse pehle |
| app/document_parser.py | Gemini extraction / fixed mock | Calculator ke baad |
| app/classifier.py | TF-IDF + MLP training/inference | Parser ke baad |
| app/retrieval.py | TF-IDF factor search | Classifier ke baad |
| app/agent.py | Sab steps coordinate karta hai | Components samajhne ke baad |
| app/report_generator.py | Narrative aur ReportLab PDF | Processing ke baad |
| main.py | FastAPI routes | Core flow ke baad |
| frontend/streamlit_app.py | User input/display/download | API ke saath compare karo |
| data/training_data.json | Classifier ke labeled examples | Training lesson mein |
| tests/test_calculator.py | Selected calculator checks | Calculator lesson ke saath |
| tests/test_classifier.py | Selected classifier checks | Classifier lesson ke saath |

## 5. Factor table aur lookup

`EmissionFactor` ek dataclass hai. Usme activity, unit, multiplier, scope, category aur description fields hain. `EMISSION_FACTORS` dictionary keys ko factors se map karti hai.

Actual helper:

```python
def get_factor(activity_key: str) -> EmissionFactor:
    if activity_key not in EMISSION_FACTORS:
        raise KeyError(f"No emission factor found for activity '{activity_key}'")
    return EMISSION_FACTORS[activity_key]
```

Line by line: category key check hui; unknown key pe explicit error; known key pe factor return. Yeh AI prediction nahi, dictionary lookup hai.

`list_factors_by_scope` matching scope ke factors filter karta hai. `search_factors_text` factor ki activity/category/description/unit ko searchable text mein combine karta hai. Retriever ko numeric factor ki jagah yeh descriptive text useful hai.

Interview follow-up: factor year/geography/source kaise version karoge? Answer: input context ke saath applicable version choose karna aur selected source/version audit mein preserve karna useful improvement hai. Current dataclass mein complete version provenance nahi hai.

## 6. Calculator ka code reading

Input class:

```python
@dataclass
class ActivityRecord:
    activity_key: str
    quantity: float
    source_label: str = ""
```

`activity_key` identifies factor. `quantity` factor ke native unit mein expected hai. `source_label` invoice reference/description rakh sakta hai. Notice: `source_unit` field nahi hai.

Actual calculation ka relevant part:

```python
report = EmissionsReport()
for act in activities:
    factor: EmissionFactor = get_factor(act.activity_key)
    emissions_kg = act.quantity * factor.factor_kgco2e
    report.records.append(
        EmissionResult(
            activity_key=act.activity_key,
            quantity=act.quantity,
            unit=factor.unit,
            factor_kgco2e=factor.factor_kgco2e,
            emissions_kgco2e=round(emissions_kg, 3),
            emissions_tco2e=round(emissions_kg / 1000, 5),
            scope=factor.scope,
            category=factor.category,
            source_label=act.source_label,
        )
    )
```

- Empty report object bana.
- Har activity ke liye factor lookup hua.
- Quantity aur factor multiply hue.
- Result record mein numeric output aur context store hua.
- Record report ki list mein append hua.

Function ke end pe report return hota hai. `EmissionResult` output record ka structure hai. `EmissionsReport` multiple result records ko hold/aggregate karti hai.

Actual scope total method:

```python
def total_by_scope(self, scope: int) -> float:
    return round(
        sum(r.emissions_tco2e for r in self.records if r.scope == scope), 4
    )
```

Normal loop mein same idea: total 0 se start; record ka scope matching ho toh tonnes add; final total round. Generator syntax se darna nahi, operation simple filter-plus-sum hai.

Baaki methods: `total_by_category` category-wise dictionary totals banata hai; `grand_total` sab records add karta hai; `summary` scope totals, category totals aur Scope 3 percentage return karta hai. Empty report ka total zero hai; percentage calculation denominator zero hone par 0 return karti hai.

### Important bug class: wrong units

2 MWh aur 2 kWh same nahi. 2 MWh = 2,000 kWh. Parser unit return karta hai, lekin agent ActivityRecord banate waqt unit discard kar deta hai. Calculator assumption pe depend karta hai ki quantity already native unit mein hai.

Improve karne ki practice: source unit preserve karo; valid conversions implement karo; incompatible unit reject karo. Demo electricity factor pe 2 MWh aur 2,000 kWh dono 1.432 tonnes dene chahiye. Yeh proposed improvement hai, current implementation nahi.

## 7. Parser: messy text se structured data

`extract_activity_data(raw_text)` model se JSON array mangta hai. Har line item mein description, quantity, unit aur source_label expected hain. `_get_client` environment key/dependency check karta hai. `_mock_extract` credentials unavailable hone par fixed example deta hai.

Expected extraction ka illustrative example:

```json
[
  {
    "description": "diesel for backup generator",
    "quantity": 100,
    "unit": "litre",
    "source_label": "INV-001"
  }
]
```

LLM ko extraction kyun diya? Supplier text formats vary karte hain. Lekin LLM se received array ko strongly validate karna abhi improvement area hai. Valid JSON ka list hona, har field type, positive/finite quantity aur usable unit separate checks hain.

Current failure cases: malformed JSON pe parser `[]` return kar sakta hai, jo valid empty document jaisa dikh sakta hai. Wrong top-level structure downstream break kar sakta hai. Remote exceptions ke liye robust retry/review path complete nahi hai.

Scanned PDF image se text nikalna OCR hai. Current parser ko text input chahiye. Isko complete OCR implementation mat describe karna.

**Mock warning samajho:** Key nahi hai toh invoice mein 100/200/change kuch bhi likho, parser fixed 450-litre diesel example return karta hai. Screen pe result dikhna extraction quality ka proof nahi.

## 8. Classifier: text ko known category dena

Training dataset ke 48 examples aur 15 labels hain. Example input text `"diesel fuel invoice"`, label `"diesel_litre"`. Extraction aur classification alag jobs hain: parser quantity/data nikalta hai; classifier category choose karta hai.

Actual pipeline definition:

```python
pipeline = Pipeline([
    ("tfidf", TfidfVectorizer(ngram_range=(1, 2), min_df=1, stop_words="english")),
    ("nn", MLPClassifier(
        hidden_layer_sizes=(64, 32),
        activation="relu",
        solver="adam",
        max_iter=2000,
        random_state=42,
    )),
])
pipeline.fit(texts, labels)
```

`load_training_data` JSON se texts aur labels ki separate lists banata hai. TF-IDF text ko numeric features mein convert karta hai. MLP features ko labels se relate karna learn karta hai. Pipeline dono components ek object mein rakhti hai.

`train_classifier(save=True)` fit karke optional joblib file save karta hai. `load_classifier` saved file available ho toh load karta hai; absent ho toh train/save karta hai. Startup pe training possible hai, isliye lifecycle samjho.

Actual inference:

```python
proba = model.predict_proba([text])[0]
classes = model.classes_
best_idx = proba.argmax()
predicted_label = classes[best_idx]
confidence = float(proba[best_idx])
```

`[text]` ek-element input batch hai. `[0]` first input ki output probabilities leta hai. `argmax` highest score ka index deta hai. Same index `classes_` se label identify karta hai.

Example probabilities `[0.70, 0.20, 0.10]` aur labels `[diesel, electricity, freight]` ho toh diesel choose hoga. Yeh explanatory example hai, actual model output nahi.

`confidence < 0.55` low-confidence flag banata hai. 0.54 escalate, exactly 0.55 local accept. Display confidence rounded hai, comparison original value pe hai. Threshold held-out data se tuned/validated hai, aisa evidence nahi mila.

Interview mein "MLP better than every simpler classifier" mat bolo. TF-IDF + logistic regression baseline compare karna sensible experiment hai. Confidence calibration, representative labels aur class-wise errors bhi chahiye.

## 9. Retriever: evidence search

`EmissionFactorRetriever.__init__` searchable factor texts collect karta hai, vocabulary fit karta hai aur matrix banata hai. Query ke waqt same vocabulary use hoti hai.

Actual ranking ka part:

```python
query_vec = self.vectorizer.transform([query])
sims = cosine_similarity(query_vec, self.matrix)[0]
top_idx = np.argsort(sims)[::-1][:top_k]
```

Query vector bana; har factor vector se cosine similarity nikli; `argsort` indices ascending order mein deta hai; `[::-1]` reverse; `[:top_k]` top candidates. Result objects key, score aur context rakhte hain.

TF-IDF related words pe useful hai. Synonym/meaning-only match weak ho sakta hai. Query ke saare terms unknown ho toh zero vector/similarities ka case aa sakta hai. Phir bhi ranking candidates de sakti hai. Top candidate hona strong evidence nahi.

## 10. Agent: coordinator kya decide karta hai?

`CarbonLedgerAgent.__init__`: classifier load, retriever setup, Gemini client optional. `_escalate_to_llm`: top-3 candidates lo, candidate context prompt mein do, response JSON parse karo. `process_document`: main loop.

Actual agent ka selected branch:

```python
if not cls_result["needs_llm_review"]:
    activity_key = cls_result["predicted_activity_key"]
else:
    llm_result = self._escalate_to_llm(desc)
    activity_key = llm_result.get("activity_key", "UNMATCHED")
```

Original branches audit entries bhi append karti hain, jo snippet mein nahi dikhaye. `AuditEntry` description, decision_source, selected activity_key aur score/reason rakhte hain. `AgentRunResult` emissions_report, audit_trail aur unmatched_items combine karta hai.

`UNMATCHED` item skip hoke unmatched list mein jata hai. Normal key ActivityRecord banakar calculator ko jaati hai. Unknown non-UNMATCHED key factor lookup pe crash kar sakti hai.

Prompt bolta hai candidates mein se choose karo. Current code selected key ki candidate membership enforce nahi karta. Interview lesson: natural-language instruction ko runtime validation ka replacement mat samjho.

Without key, escalation top TF-IDF candidate use karti hai. Reasoning mein mock label hota hai, lekin coordinator decision_source `llm_escalation` hi set karta hai. Logging semantics ka improvement yahan possible hai.

Agent ko bound pipeline/coordinator kehna accurate hai. Isme completely open-ended autonomous planning, arbitrary tools ya distributed workers implement hue hain, aisa claim mat karo.

## 11. Report generation

`generate_narrative(summary)` numbers ko text explanation mein convert karne ke liye Gemini use karta hai. `_mock_narrative` fallback text banata hai. `build_pdf_report` company, period, summary, narrative aur audit count se PDF banata hai.

Important: calculation numbers source of truth hone chahiye. Narrative unka description hai; generated prose unhe change/misstate kar sakti hai, isliye numeric consistency check useful hai. Current PDF complete line-by-line audit records embed nahi karti.

ReportLab ka kaam layout/file creation hai. Gemini PDF engine nahi. Methods ke parameter names reference file mein dekho; return/path behavior entry point mein trace karo.

## 12. API aur UI ko connect karo

FastAPI `main.py` mein:

- `GET /`: Service aur key configured hone ka status.
- `POST /process`: Text process; summary, audit, unmatched return.
- `POST /generate-report`: Processing plus narrative/PDF; local report_path return.
- `GET /health`: Basic running status.

Actual route ka part:

```python
@app.post("/process")
def process_document(req: ProcessTextRequest):
    result = agent.process_document(req.document_text)
    return {
        "summary": result.emissions_report.summary(),
        "audit_trail": [vars(a) for a in result.audit_trail],
        "unmatched_items": result.unmatched_items,
    }
```

Pydantic request model document_text field define karta hai. `vars(a)` object ke attributes ko dict form mein deta hai. Response API client ko useful data provide karta hai.

Streamlit text_area input, run/report buttons, scope metrics, category chart, audit table aur download button banata hai. `st.session_state.agent` reruns ke beech agent object retain karta hai. Is UI se current code direct Python method call karta hai, FastAPI request nahi.

Report path banana aur deployed public downloadable file serve karna alag concerns hain. Company name se path banana robust filename validation/collision handling demand karta hai. Yeh production improvement topic hai.

## 13. Tests ko samjho

Calculator suite: single activity, scope totals, empty input, invalid key aur category aggregation. Classifier suite: train success, known diesel category aur score/escalation result fields. Total 8 test functions.

Actual assertion:

```python
assert report.records[0].emissions_kgco2e == 268.0
```

Yeh particular input pe arithmetic output check karta hai. Live extraction, all categories ki generalization, API failure handling aur reporting compliance prove nahi karta. Full suite is review mein run nahi hui. Basic deterministic arithmetic separately check hua tha.

## 14. Cost aur resume claims

100 classifications ko LLM dene ki baseline versus sirf 10 escalations: classification calls 90% kam. Lekin extraction aur narrative ki 2 calls add hon toh total 102 se 12 hota hai, about 88.2% reduction. Yeh illustration hai, measured repo benchmark nahi.

Claim defend karne ke liye dataset, expected labels, accepted errors, baseline, call counters aur tokens/time preserve karo. "Full audit logging" ke liye current in-memory decision list ko durable audit store mat bolo. "ESRS/CSRD aligned" ko demo structure/factors ki limitation ke saath explain karo.

## 15. Interview-ready explanation, apne words mein bolo

"CarbonLedger invoice text ko activity records mein convert karne wala prototype hai. Gemini extraction karta hai, local TF-IDF/MLP category predict karta hai aur low-confidence items retrieved candidates ke saath Gemini ko escalate hote hain. Emissions arithmetic Python calculator mein fixed hai. API/UI summary aur decision records expose karte hain, aur ReportLab report banata hai. Current limitations mein small synthetic training set, unit validation aur persistent audit storage aate hain."

Is answer ka har phrase code mein locate kar pao. Follow-ups `04` mein hain. Pehle practice tasks: quantity 200 predict karo, total_by_scope normal loop mein likho, unit mismatch explain karo, phir threshold gate khud implement karo.

Source: [pinned CarbonLedger snapshot](https://github.com/sp-ankitprajapati/carbonledger/tree/a63f7825724a75953952cf071e2200a099bc9316). Scope background: [GHG Protocol](https://ghgprotocol.org/calculation-tools-faq). Probability context: [scikit-learn calibration](https://scikit-learn.org/stable/modules/calibration.html).
