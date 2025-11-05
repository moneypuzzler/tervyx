# DOI 교체 가이드

현재 모든 엔트리는 합성 DOI (`10.1234/...`)를 사용하고 있습니다. 실제 연구 데이터로 교체하는 방법을 설명합니다.

## 📍 DOI 위치

DOI는 **evidence.csv** 파일에 저장되어 있으며, 빌드 시 자동으로 다음 파일들로 전파됩니다:
- `citations.json` - 인용 정보
- `entry.jsonld` - 메인 엔트리 데이터

```
entries/
  └── behavioral/
      └── magnesium-slp-mag-core/
          └── sleep/
              └── v1/
                  ├── evidence.csv      ← DOI는 여기에 저장됨
                  ├── citations.json    ← 자동 생성됨
                  ├── simulation.json   ← 자동 생성됨
                  └── entry.jsonld      ← 자동 생성됨
```

## 방법 1: 수동 교체 (소규모)

### 단계 1: evidence.csv 편집

```bash
# 예: magnesium 엔트리 편집
nano entries/behavioral/magnesium-slp-mag-core/sleep/v1/evidence.csv
```

**변경 전:**
```csv
study_id,year,design,effect_type,effect_point,ci_low,ci_high,n_treat,n_ctrl,risk_of_bias,doi,journal_id,outcome,population,adverse_events,duration_weeks
SLP-MAG-CORE-01,2010,randomized controlled trial,SMD,-0.3468,-0.5046,-0.189,94,80,mixed,10.1234/slp-mag-core-01,sleep-journal-01,sleep_quality,Adults with sleep quality concerns,Transient headache,11
```

**변경 후:**
```csv
study_id,year,design,effect_type,effect_point,ci_low,ci_high,n_treat,n_ctrl,risk_of_bias,doi,journal_id,outcome,population,adverse_events,duration_weeks
SLP-MAG-CORE-01,2010,randomized controlled trial,SMD,-0.3468,-0.5046,-0.189,94,80,mixed,10.1016/j.sleep.2020.01.023,sleep-journal-01,sleep_quality,Adults with sleep quality concerns,Transient headache,11
```

### 단계 2: 엔트리 재빌드

```bash
python3 tools/build_protocol_entry.py \
  entries/behavioral/magnesium-slp-mag-core/sleep/v1 \
  --claim "Magnesium supplementation improves sleep outcomes"
```

### 단계 3: 검증

```bash
# 재빌드 성공 확인
cat entries/behavioral/magnesium-slp-mag-core/sleep/v1/citations.json | grep doi

# 전체 검증
python3 scripts/validate_entry_artifacts.py
```

## 방법 2: 스크립트를 이용한 대량 교체

대량의 DOI를 한 번에 교체하려면 매핑 파일을 만들고 스크립트를 사용합니다.

### 단계 1: DOI 매핑 파일 생성

`doi_mappings.csv` 파일을 만듭니다:

```csv
entry_path,study_id,old_doi,new_doi,pmid,notes
entries/behavioral/magnesium-slp-mag-core/sleep/v1,SLP-MAG-CORE-01,10.1234/slp-mag-core-01,10.1016/j.sleep.2020.01.023,32145678,Real study on magnesium
entries/behavioral/magnesium-slp-mag-core/sleep/v1,SLP-MAG-CORE-02,10.1234/slp-mag-core-02,10.1093/sleep/zsab123,33456789,
entries/immune/vitamin-d-imm-imm04/immune/v1,IMM-IMM04_01,10.1234/vitamin-d-imm-imm04-01,10.1136/bmj.i6583,27881684,Vitamin D meta-analysis
```

### 단계 2: 교체 스크립트 실행

```bash
python3 tools/update_dois.py --mapping doi_mappings.csv --rebuild
```

## 방법 3: PubMed/CrossRef API 사용 (자동화)

실제 연구를 찾아서 자동으로 DOI를 가져오는 방법입니다.

```bash
# PMID로 DOI 찾기
python3 tools/fetch_real_dois.py \
  --entry entries/behavioral/magnesium-slp-mag-core/sleep/v1 \
  --query "magnesium sleep quality randomized" \
  --max-studies 3

# 자동으로 최적의 연구를 찾고 effect size 추출
python3 tools/auto_populate_entry.py \
  --entry entries/behavioral/magnesium-slp-mag-core/sleep/v1 \
  --substance "magnesium glycinate" \
  --outcome "sleep quality" \
  --min-studies 3
```

## 📝 실제 DOI 찾는 방법

### 1. PubMed에서 검색
```
https://pubmed.ncbi.nlm.nih.gov/
검색어: "magnesium AND sleep quality AND randomized controlled trial"
```

### 2. CrossRef에서 검색
```
https://search.crossref.org/
DOI를 직접 검색하거나 제목으로 찾기
```

### 3. Google Scholar
```
https://scholar.google.com/
논문 제목 또는 저자로 검색 → DOI 확인
```

## ✅ DOI 형식 확인

유효한 DOI 형식:
- ✅ `10.1016/j.sleep.2020.01.023`
- ✅ `10.1093/sleep/zsab123`
- ✅ `10.1136/bmj.i6583`
- ❌ `https://doi.org/10.1016/...` (URL 형식은 안됨)
- ❌ `doi:10.1016/...` (접두사 불필요)

## 🔄 재빌드 후 확인사항

1. **citations.json 확인**
   ```bash
   cat entries/.../citations.json | jq '.studies[].doi'
   ```

2. **journal_id 업데이트 필요 여부**
   - 실제 저널명으로 변경 (예: `sleep-journal-01` → `Sleep Medicine`)
   - Journal Trust Oracle에서 평가 가능하도록

3. **검증 통과**
   ```bash
   python3 scripts/validate_entry_artifacts.py
   ```

## 📊 대량 작업 워크플로우

전체 200개 엔트리를 실제 데이터로 교체하는 권장 순서:

1. **우선순위 선정** (예: sleep, cognition 등 중요한 카테고리)
2. **문헌 조사** (각 substance + outcome 조합에 대한 실제 메타분석/RCT 찾기)
3. **DOI 매핑 파일 작성**
4. **배치 처리 실행**
5. **검증 및 커밋**

## 🚨 주의사항

- **Effect size를 새로 계산해야 할 수 있음**: 실제 논문의 데이터가 현재 합성 데이터와 다를 경우
- **Journal Trust Score**: 실제 저널은 J-gate 평가를 받으므로 일부 엔트리가 낮은 점수를 받을 수 있음
- **Policy fingerprint**: DOI만 바꾸면 재빌드만 필요 (policy 변경 없음)

## 💡 팁

- 한 번에 모든 엔트리를 교체하기보다는 **카테고리별로 단계적 진행** 권장
- 실제 메타분석 논문이 있다면 그 논문의 forest plot 데이터를 사용하는 것이 가장 좋음
- 각 엔트리당 최소 3개의 RCT가 필요 (policy 요구사항)
