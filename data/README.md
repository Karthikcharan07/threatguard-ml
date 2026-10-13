# Dataset acquisition and required schema

No UNSW-NB15 CSV was supplied with this request. No real UNSW-NB15 benchmark is included.
Do not commit any full dataset to GitHub or interpret synthetic results as this benchmark.

1. Visit the official [UNSW-NB15 page](https://research.unsw.edu.au/projects/unsw-nb15-dataset).
2. Follow its current official dataset download links, accepting any access/license terms yourself.
3. Prefer the **headered prepared partitions** `UNSW_NB15_training-set.csv` and
   `UNSW_NB15_testing-set.csv`. The official page identifies 175,341 and 82,332 records respectively.
4. Place both CSV files in this `data/` directory, or use absolute CLI paths.
5. Run the real-data command in the root README. Record filtering/overlap counts in your report.

The four large raw `UNSW-NB15_1.csv`..`UNSW-NB15_4.csv` files are not drop-in inputs here.
They may have a different/headerless schema; map them using the official feature description first.
The loader deliberately rejects unknown fields instead of silently selecting a target or hiding schema mistakes.
Use the published prepared train/test files for this academic assessment.

Binary target: `label` with only 0/1. Multiclass target: nonempty `attack_cat` strings.
Both target columns and `id` are excluded from features. Raw identifiers `srcip`, `dstip`, `sport`,
`dsport`, `stime`, `ltime` are also excluded if present. No target-derived column may be added.

Required minimum feature columns (including the synthetic fixture):
`dur, proto, service, state, spkts, dpkts, sbytes, dbytes, rate`.
All other official supported fields present in a CSV become trained features.
The external test CSV must contain the identical trained feature set (column order can differ).

Supported categorical fields: `proto`, `service`, `state`.
Supported numerical fields:
```
dur spkts dpkts sbytes dbytes rate sttl dttl sload dload sloss dloss
sinpkt dinpkt sjit djit swin stcpb dtcpb dwin tcprtt synack ackdat
smean dmean trans_depth response_body_len ct_srv_src ct_state_ttl
ct_dst_ltm ct_src_dport_ltm ct_dst_sport_ltm ct_dst_src_ltm is_ftp_login
ct_ftp_cmd ct_flw_http_mthd ct_src_ltm ct_srv_dst is_sm_ips_ports
```

Header names are stripped and lowercased. Duplicate headers fail. Numeric nulls are allowed;
infinities, nonnumeric strings, missing targets and unexpected columns fail. Each input CSV
must contain at least 20 rows, two classes and at least three observations per class. A nonoverlapping
evaluation subset must still be large enough to evaluate. CSVs larger than 1 GB are rejected to bound ingestion.

Use `python -m ml.synthetic --output data/synthetic.csv --rows 1200 --seed 42` for development.
Synthetic class labels are generated from overlapping artificial patterns with 6% random label flips.
Only the generator is shipped; generated CSVs are excluded from ZIPs/git.

For academic/public use, cite the dataset authors as requested by the official page, including:
Moustafa, N. and Slay, J. (2015), “UNSW-NB15: a comprehensive data set for network intrusion
detection systems (UNSW-NB15 network data set),” MilCIS, IEEE.
Moustafa, N. and Slay, J. (2016), “The evaluation of Network Anomaly Detection Systems:
Statistical analysis of the UNSW-NB15 data set and the comparison with the KDD99 data set,”
Information Security Journal: A Global Perspective.
