Table: TE_RAG001T

Description:
- 월별 국가별 수출입 금액을 관리하는 테이블이다.

Columns:
- ACPT_YYMM (VARCHAR, PK)
  - 기준년월
  - 형식: YYYYMM
  - 예: 202401, 202402

- CNTY_CD (VARCHAR, PK)
  - 국가코드 (ISO 2자리)
  - 예: KR, US, CN, JP

- EXP_USD_AMT (NUMBER)
  - 해당 월의 수출 금액
  - 단위: USD

- IMP_USD_AMT (NUMBER)
  - 해당 월의 수입 금액
  - 단위: USD

Primary Key:
- (ACPT_YYMM, CNTY_CD)

Business Rules:
- 모든 금액은 USD 기준이다.
- ACPT_YYMM은 문자열(YYYYMM)로 관리한다.
- CNTY_CD는 ISO 2자리 국가코드를 사용한다.
