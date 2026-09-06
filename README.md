# SmartHeartShield

A clinical decision-support analysis system for reviewing cardiac rupture risk data, providing an overview of emergency visits, supporting diagnosis, and tracking the course of a patient's condition.

## Data Scope

At runtime, the system reads only `clean_非破裂完整版（15天窗口）.xlsx` from the project root. It does not modify the original workbook or generate synthetic patient data. The current cleaned workbook has the following baseline statistics:

- 5,348 patients (deduplicated by `regno`)
- 14,419 encounter records (distinguished by `regno + admno`)
- 5,063 patients with multiple encounters
- 0 records with `label=1`; all valid records are retrospective non-rupture samples
- 1,807 encounter records with confirmed surgical or interventional procedures

`label` is displayed only as a retrospective target-event label from the workbook. It does not represent a predicted probability, risk level, mortality outcome, or real-time alert. `cutoff_time` indicates only the end of the 15-day data window; it is not a predicted rupture time. The workbook itself contains no verifiable model-based risk stratification or predicted-time fields. The `heart_break_predict_results.json` file in the project root is used to display the overall distribution of 211 true-positive samples from the model validation set. Through a deterministic demo mapping, it also supplies display data for patient risk cards on the **Condition Details** page; this mapping does not call an online prediction service. Day-level rupture timing is explicitly labeled in the interface as a demonstration estimate.

The workbook path can be overridden through an environment variable or `.streamlit/secrets.toml`:

    PATIENT_WORKBOOK_XLSX = "D:/path/to/clean_非破裂完整版（15天窗口）.xlsx"

## Pages

- **Home:** The system's purpose, data scope, and entry points to its three main features.
- **Emergency Overview:** Reads `heart_break_predict_results.json` directly to display model validation samples with risk stratification, severity, tiered treatment recommendations, combined filters, sorting, and numbered pagination. It does not call an online prediction service.
- **Diagnostic Assistance:** Filters by patient and encounter, prioritizing patients whom the model identifies as potentially at risk of cardiac rupture based on uploaded prediction results. It provides Agent-assisted Q&A with a traceable tool-call process. Q&A history is persisted per encounter. When switching patients, the chat stream on the right remains continuous and identifies which record each message belongs to, while the model context remains limited to the current encounter. The system deletes the complete Q&A history on the right only when the user explicitly clicks **Clear Conversation**.
- **Condition Details:** Displays a single encounter strictly by `regno + admno`. At the top of the page, it first summarizes all demo-mapped cases predicted by the model as potentially experiencing cardiac rupture, including counts of successful and failed predictions and the success rate. It then summarizes the current patient's encounter period, primary diagnosis, treatment or surgery, and retrospective target event. The risk tab presents a deterministic demo mapping of uploaded results into high-, medium-, and low-risk groups, together with an individual risk simulation.
- **About:** System information, data sources, and clinical safety boundaries.

## Getting Started

Run the following commands in the project directory:

    python -m pip install -r requirements.txt
    python -m streamlit run app.py

Open http://localhost:8501 in a browser.

## Verification

    python -m py_compile app.py config.py agent\*.py components\*.py services\*.py views\*.py
    python -m unittest discover -s tests -v

## Agent and Prediction Model Configuration

The model-integration components from `Xindun` have been incorporated into this project, including the Bailian ReAct Agent, a general medical knowledge model, preparation of pre-cutoff clinical data, a dual-endpoint failover client for the cardiac rupture prediction model, and a resumable batch prediction pipeline. The actual Qwen2.5-7B model weights are located at `D:/Personal/Desktop/xinzangpolie/model`, and the training and evaluation code uses dual-GPU inference with vLLM. The current web application does not load the 15 GB model weights directly into the Streamlit process; instead, it calls an OpenAI-compatible inference service.

Copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`, then configure the following values:

- `DASHSCOPE_API_KEY`: API key for the Bailian Agent and knowledge model.
- `BAILIAN_MODEL`: Primary Agent model; defaults to `qwen3.7-plus`.
- `BAILIAN_KNOWLEDGE_MODEL`: Medical knowledge explanation model; defaults to `deepseek-v4-flash`.
- `CARDIAC_RISK_URLS`: Prediction model service endpoints. Two endpoints can be configured for failover.
- `CARDIAC_RISK_MODEL`: Model name exposed by the prediction service; defaults to `cardiac-rupture-qwen38`.
- `PREDICTION_RESULTS_PATH`: Batch-results JSONL file. If omitted, results are saved under `model-results/` using the current workbook's name.
- `CHAT_HISTORY_DB_PATH`: Path to the SQLite database for Diagnostic Assistance Q&A history. If omitted, the project-root `chat_history.db` file is used.

When deploying to a server, `127.0.0.1` refers to the machine hosting the web application. If the prediction model runs on another machine, `CARDIAC_RISK_URLS` must be changed to an internal network address accessible from the web server, and the corresponding ports must be allowed through the network and firewall.

The application prepares model input from the current encounter record. It uses only records from the 15 days before `cutoff_time`, grouped into 0–48 hours, 48–72 hours, and 72–360 hours before the prediction cutoff. It excludes `regno`, `admno`, `label`, information recorded after the prediction cutoff, and aggregated events that cannot be matched reliably. The actual output contract of the uploaded model consists of a rupture assessment, current severity, and a textual explanation; it does not provide a calibrated probability or a specific rupture time. The day-level timeline shown for high-risk individuals on the Condition Details page is explicitly labeled as a **demonstration estimate** and must not be used for real-world clinical timing or intervention.

On a Linux server with two GPUs that have sufficient VRAM, an OpenAI-compatible service can be started using the model path from the original evaluation code. The ports can be set to 8000 and 8001, respectively:

    python -m vllm.entrypoints.openai.api_server --model /path/to/xinzangpolie/model --served-model-name cardiac-rupture-qwen38 --tensor-parallel-size 2 --dtype bfloat16 --max-model-len 8192 --port 8000

The project also provides `scripts/start_prediction_service.sh`. After setting `CARDIAC_RISK_MODEL_PATH`, you can use it to start the same service. To start a second instance, set `CARDIAC_RISK_PORT=8001` and launch it separately.

**Emergency Overview** no longer provides an entry point for online batch prediction. It reads only `heart_break_predict_results.json` from the project root. The online model service remains available to Diagnostic Assistance and for predictions on individual encounters that have an `encounter_key`, but it does not affect the risk colors or patient list shown in Emergency Overview.

Do not commit `.streamlit/secrets.toml` or the original workbook to a public repository. A shared password is not a substitute for the authentication, least-privilege access control, and auditing required by a formal hospital system.

The local Q&A database and its WAL/SHM temporary files are included in `.gitignore`. In production, the database must still be stored in an access-controlled persistent directory and backed up and purged in accordance with the hospital's data-governance requirements.

## Safety Boundaries

This system is intended only for clinical decision support and research analysis. It cannot replace a physician's diagnosis, intervention, or treatment decisions. All risk results must be reviewed by qualified healthcare professionals in conjunction with the complete clinical record.
