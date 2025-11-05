# DOI 매칭 전략 가이드

## 문제 정의

각 엔트리는 **substance + category + outcome** 조합입니다:
- 예: `magnesium` + `sleep` + `sleep_quality`
- 예: `magnesium` + `cardiovascular` + `blood_pressure`

**같은 substance라도 category가 다르면 완전히 다른 연구가 필요합니다.**

## 📊 현재 상황

```
총 200개 엔트리 × 각 3개 연구 = 600개 DOI 필요
```

### 엔트리 분포
- Behavioral (sleep): 19개
- Immune: 41개
- Metabolic: 43개
- Neurological (cognition): 21개
- Physiological (cardiovascular, musculoskeletal): 44개
- Psychological (mental_health): 31개
- Safety: 1개

## 🎯 매칭 전략

### 1단계: 요구사항 추출 ✅

`entry_requirements.csv` 파일 생성됨:
```csv
substance,substance_id,category,domain,outcome,population,n_studies,entry_path,needs_real_dois
5htp,5htp-slp-fhtp-serotonin,sleep,behavioral,sleep_quality,Adults with sleep quality concerns,3,entries/behavioral/5htp-slp-fhtp-serotonin/sleep/v1,yes
```

### 2단계: 논문 검색 전략

각 substance-category 조합에 대해 다음 검색 쿼리 사용:

```
"[substance] AND [outcome] AND randomized controlled trial"
```

**예시:**
- `"magnesium AND sleep quality AND randomized controlled trial"`
- `"curcumin AND systemic inflammation AND RCT"`
- `"omega-3 AND depression AND randomized trial"`

### 3단계: 초록 검증 (매우 중요!)

찾은 논문이 해당 outcome을 실제로 다루는지 확인:

```python
# 초록에서 확인할 키워드
outcome_keywords = {
    "sleep_quality": ["PSQI", "sleep quality", "sleep efficiency"],
    "depression": ["PHQ-9", "BDI", "depression score", "HAM-D"],
    "blood_pressure": ["systolic", "diastolic", "BP", "mmHg"],
    "inflammation": ["CRP", "IL-6", "TNF-alpha", "inflammatory markers"]
}
```

### 4단계: DOI 매핑 생성

매칭된 논문에 대해:
```csv
entry_path,study_id,old_doi,new_doi,pmid,outcome_verified,notes
entries/behavioral/magnesium-slp-mag-core/sleep/v1,SLP-MAG-CORE-01,10.1234/...,10.1684/mrh.2010.0220,20920146,yes,Nielsen 2010 - PSQI improvement
```

## 🔧 자동화 도구

### Option A: 반자동 워크플로우 (권장)

```bash
# 1. 카테고리별로 논문 리스트 수동 큐레이션
# sleep 관련 논문들을 spreadsheet에 정리
# - substance, outcome, DOI, PMID, abstract_keywords

# 2. 매칭 스크립트 실행
python3 tools/match_dois.py --category sleep --input sleep_papers.csv

# 3. 결과 검토 후 적용
python3 tools/update_dois.py --mapping sleep_matched.csv --rebuild
```

### Option B: PubMed API 활용

```python
from Bio import Entrez

def search_pubmed(substance, outcome):
    query = f"{substance} AND {outcome} AND randomized controlled trial"
    # Search PubMed
    # Parse results
    # Extract DOIs
    pass
```

### Option C: 완전 자동 (WebSearch 활용)

```bash
# 배치로 나눠서 실행
python3 tools/auto_find_dois.py --batch 1 --size 20
# 20개씩 처리, WebSearch로 논문 찾기
```

## 📋 우선순위 추천

### High Priority (먼저 처리)
1. **Sleep (19 entries)** - 이미 8개 완료
   - 남은 11개: melatonin, GABA, 5-HTP, kava, lemon balm, passionflower, inositol, tryptophan, CBD microdose, mag threonate, matcha

2. **Mental Health - Depression/Anxiety (31 entries)**
   - Omega-3, SAM-e, St John's Wort, Saffron, L-theanine, Lavender 등
   - 많은 연구가 있는 분야

3. **Cognition (21 entries)**
   - Bacopa, Lion's Mane, Ginkgo, Rhodiola, Alpha-GPC 등

### Medium Priority
4. **Cardiovascular (physiological)**
5. **Immune/Inflammation**

### Low Priority
6. **Longevity** - 연구 적음, 합성 데이터로도 충분할 수 있음
7. **Safety** - 특수 목적

## 🚦 매칭 체크리스트

각 DOI 매칭 시 확인사항:

- [ ] Substance가 정확히 일치하는가?
- [ ] Outcome이 측정되었는가? (PSQI, BDI, CRP 등)
- [ ] RCT 디자인인가?
- [ ] Adult population인가?
- [ ] Sample size가 합리적인가? (n>20)
- [ ] 영어 논문인가?
- [ ] Peer-reviewed 저널인가?

## 💡 Tip: 메타분석 활용

각 카테고리별로 **메타분석 논문**을 먼저 찾으면 효율적:

```
"[substance] AND [outcome] AND meta-analysis"
```

메타분석의 forest plot에서 개별 RCT들의 데이터를 가져올 수 있음!

**예:**
- "Magnesium AND sleep quality AND meta-analysis"
  → 메타분석 1개 찾으면 그 안에 5-10개 RCT가 있음

## 📄 예시: Magnesium Sleep 매칭 과정

1. **검색**: "magnesium AND sleep quality AND RCT"
2. **찾은 논문**: Nielsen 2010 (PMID: 20920146)
3. **초록 검증**:
   ```
   "...measured sleep quality using the Pittsburgh Sleep Quality Index (PSQI)..."
   ✅ Outcome 일치: PSQI는 sleep_quality의 표준 척도
   ```
4. **Effect size 확인**: SMD = -0.35 (sleep 개선, negative는 beneficial)
5. **DOI 추출**: 10.1684/mrh.2010.0220
6. **매핑 생성**: ✅

## 🔄 배치 처리 전략

1. **Sleep 남은 11개** → 1시간
2. **Mental Health 31개** → 3시간
3. **Cognition 21개** → 2시간
4. **나머지 카테고리** → 카테고리별 1-2시간

**총 예상 시간: 10-15시간**

단계별로 나눠서 처리하고 각 배치마다 검증 후 커밋하는 것을 권장합니다.
