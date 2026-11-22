# Section 4: Scaling ML Inference for 200 Million Courses

## Why It Takes 2 Months (The Bottleneck)
Processing 200 million records in 2 months is only **~38 records per second**. The pipeline is slow because:
1. **Network overhead:** Sending 200 million separate API requests wastes time on HTTP connections instead of running the model.
2. **One-by-one execution:** The script waits for each request to finish before sending the next.
3. **Batch size of 1:** Sending one description at a time underutilizes the SageMaker instance's CPU/GPU.

---

## How to Fix It

### 1. SageMaker Side (Model Serving)
* **Switch to SageMaker Batch Transform:** Put the 200M descriptions in S3 and run a Batch Transform job. SageMaker splits the files across multiple machines, processes them in batches directly, saves results to S3, and shuts down automatically.
* **Or batch & scale the Real-Time Endpoint:** Update the endpoint to accept a list of 64–128 descriptions per request, use a GPU instance, and temporarily scale up to multiple instances.

### 2. Script Side (Client Pipeline)
* **Group into batches:** Send 64–128 descriptions per API call instead of 1 (cuts API calls by >100x).
* **Send requests in parallel:** Use async calls (`asyncio`) or a thread pool instead of a sequential loop, with retries for rate limits.
* **Deduplicate first:** Only run the model on unique course descriptions, then map results back to duplicate rows.
* **Use distributed workers:** Run the script on AWS Glue or Spark to process partitions in parallel.

---

## Result
This reduces total runtime from **2 months to ~1–2 hours**.