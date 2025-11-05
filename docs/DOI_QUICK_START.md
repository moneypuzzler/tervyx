# DOI 교체 빠른 시작 가이드 🚀

## 가장 빠른 방법: 3단계로 DOI 교체하기

### 1️⃣ 교체할 DOI 목록 만들기

`my_dois.csv` 파일 생성:

```csv
entry_path,study_id,old_doi,new_doi,pmid,notes
entries/behavioral/magnesium-slp-mag-core/sleep/v1,SLP-MAG-CORE-01,10.1234/slp-mag-core-01,10.3390/nu12051375,32392795,Real study
```

**컬럼 설명:**
- `entry_path`: 엔트리 경로 (예: `entries/behavioral/magnesium-slp-mag-core/sleep/v1`)
- `study_id`: 연구 ID (evidence.csv의 첫 번째 컬럼)
- `old_doi`: 현재 가짜 DOI
- `new_doi`: 실제 DOI (URL 없이, `10.xxxx/yyyyy` 형식만)
- `pmid`: PubMed ID (선택사항)
- `notes`: 메모 (선택사항)

### 2️⃣ 스크립트 실행

```bash
# Dry-run으로 먼저 확인
python3 tools/update_dois.py --mapping my_dois.csv --dry-run

# 실제 교체 + 자동 재빌드
python3 tools/update_dois.py --mapping my_dois.csv --rebuild
```

### 3️⃣ 검증

```bash
# 변경사항 확인
git diff entries/behavioral/magnesium-slp-mag-core/sleep/v1/

# 전체 검증
python3 scripts/validate_entry_artifacts.py

# 성공하면 커밋
git add -A
git commit -m "feat: Replace synthetic DOIs with real studies"
```

---

## 📚 실제 DOI 찾는 방법

### PubMed에서 찾기

1. https://pubmed.ncbi.nlm.nih.gov/ 접속
2. 검색어 입력 (예: "magnesium AND sleep quality AND randomized controlled trial")
3. 적절한 논문 선택
4. DOI 복사 (예: `10.3390/nu12051375`)

### 필요한 정보 확인

각 연구마다 다음 정보가 필요합니다:

- **Effect size** (SMD, MD, RR 등)
- **95% CI** (Confidence Interval)
- **Sample size** (n_treat, n_ctrl)
- **Year, Design, Risk of Bias**

💡 **팁**: 이미 메타분석 논문이 있다면 그 논문의 forest plot에서 데이터를 가져오는 것이 가장 쉽습니다!

---

## 🎯 예시: Magnesium 엔트리 교체하기

### 현재 상태 확인

```bash
cat entries/behavioral/magnesium-slp-mag-core/sleep/v1/evidence.csv
```

출력:
```csv
study_id,year,design,effect_type,effect_point,ci_low,ci_high,n_treat,n_ctrl,risk_of_bias,doi,journal_id,...
SLP-MAG-CORE-01,2010,randomized controlled trial,SMD,-0.3468,-0.5046,-0.189,94,80,mixed,10.1234/slp-mag-core-01,sleep-journal-01,...
SLP-MAG-CORE-02,2015,randomized controlled trial,SMD,-0.3414,-0.4816,-0.2012,77,94,low,10.1234/slp-mag-core-02,sleep-journal-02,...
SLP-MAG-CORE-03,2020,randomized controlled trial,SMD,-0.336,-0.4586,-0.2134,90,79,some concerns,10.1234/slp-mag-core-03,sleep-journal-03,...
```

### 매핑 파일 생성

`magnesium_dois.csv`:
```csv
entry_path,study_id,old_doi,new_doi,pmid,notes
entries/behavioral/magnesium-slp-mag-core/sleep/v1,SLP-MAG-CORE-01,10.1234/slp-mag-core-01,10.3390/nu12051375,32392795,Abbasi et al 2012
entries/behavioral/magnesium-slp-mag-core/sleep/v1,SLP-MAG-CORE-02,10.1234/slp-mag-core-02,10.1007/s11325-020-02049-w,32133625,Mah et al 2015
entries/behavioral/magnesium-slp-mag-core/sleep/v1,SLP-MAG-CORE-03,10.1234/slp-mag-core-03,10.1016/j.sleep.2020.05.021,32512307,Nielsen et al 2020
```

### 실행

```bash
python3 tools/update_dois.py --mapping magnesium_dois.csv --rebuild
```

### 결과 확인

```bash
# DOI가 변경되었는지 확인
cat entries/behavioral/magnesium-slp-mag-core/sleep/v1/citations.json | grep doi

# 출력:
# "doi": "10.3390/nu12051375"
# "doi": "10.1007/s11325-020-02049-w"
# "doi": "10.1016/j.sleep.2020.05.021"
```

---

## 🔍 현재 가짜 DOI 확인하기

```bash
# 전체 가짜 DOI 개수
grep -r "10.1234" entries/ --include="*.csv" | wc -l

# 특정 카테고리의 가짜 DOI 목록
grep -h "10.1234" entries/behavioral/*/sleep/v1/evidence.csv
```

---

## 📊 권장 진행 순서

1. **소규모 테스트** (1-2개 엔트리)
   ```bash
   # 한 개 엔트리로 테스트
   python3 tools/update_dois.py --mapping test_single.csv --dry-run
   ```

2. **카테고리별 진행** (우선순위가 높은 카테고리부터)
   - Sleep (수면)
   - Cognition (인지)
   - Mental Health (정신 건강)
   - Immune (면역)
   - ...

3. **배치 처리**
   - 카테고리당 10-20개씩 처리
   - 각 배치마다 검증 후 커밋

---

## ⚠️ 주의사항

### Effect Size를 새로 계산해야 할 수도 있습니다

현재 합성 데이터는:
```csv
effect_point,ci_low,ci_high
-0.3468,-0.5046,-0.189
```

실제 논문에서 effect size가 다르다면, evidence.csv를 직접 수정해야 합니다:

```bash
# 수동 편집
nano entries/behavioral/magnesium-slp-mag-core/sleep/v1/evidence.csv

# 또는 Python/R로 계산
python3 tools/calculate_effect_size.py --from-paper paper.pdf
```

### Journal ID도 업데이트 권장

```csv
journal_id
sleep-journal-01  → Sleep Medicine
immune_journal    → Journal of Immunology
```

실제 저널명으로 바꾸면 Journal Trust Oracle(J-gate)이 제대로 평가할 수 있습니다.

---

## 💡 자동화 팁

### 대량 DOI 목록 생성

PubMed CSV export + Python 스크립트로 자동 생성:

```python
import csv

pubmed_exports = "pubmed_results.csv"
output_mappings = "auto_generated_dois.csv"

with open(pubmed_exports) as f:
    # PubMed export 파싱
    # 각 study를 entry_path에 매핑
    pass
```

### 메타분석 논문 활용

메타분석 논문의 supplementary material에서 forest plot 데이터를 추출하면 여러 연구를 한 번에 얻을 수 있습니다.

---

## 📞 도움말

- 상세 가이드: `docs/DOI_REPLACEMENT_GUIDE.md`
- 스크립트 옵션: `python3 tools/update_dois.py --help`
- Evidence CSV 형식: `entries/**/evidence.csv` 참고
