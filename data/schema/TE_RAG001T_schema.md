Table: TE_RAG001T

Description:
- 월별 국가별 / 품목별 수출입 실적을 관리하는 테이블이다.
- 국가코드와 HS 품목코드를 기준으로 수출입 금액과 중량을 관리한다.

Columns:
- ACPT_YYMM (VARCHAR, PK)
  - 기준년월
  - 형식: YYYYMM
  - 예: 202401, 202402

- CNTY_CD (VARCHAR, PK)
  - 국가코드 (ISO 2자리)
  - 예: KR, US, CN, JP

- HS_SGN (VARCHAR, PK)
  - HS 10자리 품목코드
  - 예: 8703909000

- HS2_SGN (VARCHAR)
  - HS 2자리 품목코드
  - 예: 87

- HS4_SGN (VARCHAR)
  - HS 4자리 품목코드
  - 예: 8703

- HS6_SGN (VARCHAR)
  - HS 6자리 품목코드
  - 예: 870390

- EXP_WGHT (NUMBER)
  - 수출 중량
  - 단위: KG

- 193 (NUMBER)
  - 수출 금액
  - 단위: USD

- IMP_WGHT (NUMBER)
  - 수입 중량
  - 단위: KG

- IMP_USD_AMT (NUMBER)
  - 수입 금액
  - 단위: USD

Primary Key:
- (ACPT_YYMM, CNTY_CD, HS_SGN)

Business Rules:
- HS_SGN은 HS 10자리 품목코드이다.
- HS2_SGN, HS4_SGN, HS6_SGN은 HS_SGN에서 앞자리 기준으로 생성된다.
- 모든 금액은 USD 기준이다.
- ACPT_YYMM은 문자열(YYYYMM)로 관리한다.
- CNTY_CD는 ISO 2자리 국가코드를 사용한다.

Join Rules:
- 국가명 조회 TE_RAG001T.CNTY_CD = TE_RAG917M.CNTY_CD
- 2단위 품목명 조회 TE_RAG001T.HS2_SGN = TE_RAG901M.HS_SGN AND TE_RAG901M.HS_LEVEL = '02'
- 4단위 품목명 조회 TE_RAG001T.HS4_SGN = TE_RAG901M.HS_SGN AND TE_RAG901M.HS_LEVEL = '04'
- 6단위 품목명 조회 TE_RAG001T.HS6_SGN = TE_RAG901M.HS_SGN AND TE_RAG901M.HS_LEVEL = '06'
- 10단위 품목명 조회 TE_RAG001T.HS_SGN = TE_RAG901M.HS_SGN AND TE_RAG901M.HS_LEVEL = '10'
