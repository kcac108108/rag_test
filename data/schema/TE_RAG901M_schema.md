Table: TE_RAG901M

Description:
- HS 코드부호 관리 테이블이다.
- HS 코드 레벨(2자리, 4자리, 6자리, 10자리)에 따라 품목코드와 표준품명을 관리한다.
- 품목명 조회를 위해 TE_RAG001T 테이블과 조인하여 사용한다.

Columns:

- HS_LEVEL (VARCHAR2, PK)
  - 품목코드 레벨
  - '02' : 2자리 품목
  - '04' : 4자리 품목
  - '06' : 6자리 품목
  - '10' : 10자리 품목

- HS_SGN (VARCHAR, PK)
  - 품목코드
  - HS_LEVEL에 따라 자리수가 결정된다.
  - 예:
    - 02 → 87
    - 04 → 8703
    - 06 → 870390
    - 10 → 8703909000

- HS_NM (VARCHAR)
  - 표준품명 (한글 품목명)
  - 예:
    - 일반차량
    - 승용차
    - 기타 자동차

Primary Key:
- (HS_LEVEL, HS_SGN)

Business Rules:
- HS_LEVEL 값은 품목코드 자리수를 의미한다.
- HS_SGN은 해당 레벨의 HS 코드이다.
- HS_NM은 해당 품목코드의 한글 표준품명이다.
- 동일한 HS 코드라도 레벨이 다르면 다른 레코드로 관리한다.

Join Rules:
- 2단위 품목 조회
  TE_RAG001T.HS2_SGN = TE_RAG901M.HS_SGN
  AND TE_RAG901M.HS_LEVEL = '02'

- 4단위 품목 조회
  TE_RAG001T.HS4_SGN = TE_RAG901M.HS_SGN
  AND TE_RAG901M.HS_LEVEL = '04'

- 6단위 품목 조회
  TE_RAG001T.HS6_SGN = TE_RAG901M.HS_SGN
  AND TE_RAG901M.HS_LEVEL = '06'

- 10단위 품목 조회
  TE_RAG001T.HS_SGN = TE_RAG901M.HS_SGN
  AND TE_RAG901M.HS_LEVEL = '10'