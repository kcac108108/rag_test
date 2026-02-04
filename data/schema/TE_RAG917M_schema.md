Table: TE_RAG917M

Description:
- 국가코드(CNTY_CD)와 국가명(한글, CNTY_NM)을 매핑하는 마스터 테이블이다.
- 실적 테이블(TE_RAG001T)의 CNTY_CD와 조인하여 국가명을 표시할 때 사용한다.

Columns:
- CNTY_CD (VARCHAR2, PK)
  - 국가코드 (ISO 2자리)
  - 예: KR, US, CN, JP

- CNTY_NM (NVARCHAR2)
  - 국가명(한글)
  - 예: 대한민국, 미국, 중국, 일본

Primary Key:
- (CNTY_CD)

Business Rules:
- CNTY_CD는 2자리 ISO 국가코드로 관리한다.
- CNTY_NM은 한글 국가명으로 관리한다.
- TE_RAG001T.CNTY_CD = TE_RAG917M.CNTY_CD 로 조인한다.
