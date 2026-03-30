Examples for TE_RAG001T Growth Rate Queries

Purpose:
- 증감률 / 증가율 / 감소율 / 전년대비 / 전년동기대비 질문에 대해
  올바른 Oracle SQL 패턴을 유도하기 위한 예시 모음이다.
- 특히 0으로 나누기 방지, NULL 처리, 순위 계산 규칙을 학습시키는 데 목적이 있다.


Rule Summary:
- 증감률 계산 시 분모가 되는 이전값은 반드시 NULLIF(이전값, 0) 또는 이전값 > 0 조건으로 보호한다.
- 순위 계산 시 NULL 증감률은 상위에 오면 안 되므로 DESC NULLS LAST를 사용한다.
- Oracle에서는 RANK() / DENSE_RANK() / ROW_NUMBER()를 WHERE 또는 HAVING에서 직접 사용하지 않는다.
- 순위 질의는 반드시 CTE 또는 서브쿼리로 한 번 감싼 후 바깥에서 WHERE RNK = N 형태로 필터링한다.


Example 1
Question:
2026년 기준 전년대비 수입금액 합계 증감률을 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.IMP_USD_AMT) AS IMP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG917M M
      ON T.CNTY_CD = M.CNTY_CD
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        MAX(CASE WHEN YY = '2026' THEN IMP_USD_AMT_SUM END) AS IMP_2026,
        MAX(CASE WHEN YY = '2025' THEN IMP_USD_AMT_SUM END) AS IMP_2025
    FROM BASE
    GROUP BY
        CNTY_CD,
        CNTY_NM
)
SELECT
    CNTY_CD AS "국가코드",
    CNTY_NM AS "국가명",
    IMP_2026 AS "2026년수입금액",
    IMP_2025 AS "2025년수입금액",
    ((IMP_2026 - IMP_2025) / NULLIF(IMP_2025, 0)) * 100 AS "증감률(%)"
FROM PIVOTED
ORDER BY "증감률(%)" DESC NULLS LAST
FETCH FIRST 200 ROWS ONLY;


Example 2
Question:
2026년 기준 전년동기대비 수입금액 합계 증감률 3위 국가는 어디인가

SQL:
WITH BASE AS (
    SELECT
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.IMP_USD_AMT) AS IMP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG917M M
      ON T.CNTY_CD = M.CNTY_CD
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        MAX(CASE WHEN YY = '2026' THEN IMP_USD_AMT_SUM END) AS IMP_2026,
        MAX(CASE WHEN YY = '2025' THEN IMP_USD_AMT_SUM END) AS IMP_2025
    FROM BASE
    GROUP BY
        CNTY_CD,
        CNTY_NM
),
CALC AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        IMP_2026,
        IMP_2025,
        ((IMP_2026 - IMP_2025) / NULLIF(IMP_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE IMP_2025 > 0
),
RANKED AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        IMP_2026,
        IMP_2025,
        INC_RATE,
        RANK() OVER (ORDER BY INC_RATE DESC NULLS LAST) AS RNK
    FROM CALC
)
SELECT
    CNTY_CD AS "국가코드",
    CNTY_NM AS "국가명",
    IMP_2026 AS "2026년수입금액",
    IMP_2025 AS "2025년수입금액",
    INC_RATE AS "증감률(%)"
FROM RANKED
WHERE RNK = 3
FETCH FIRST 200 ROWS ONLY;


Example 3
Question:
2026년 기준 전년대비 수출금액 증가율 상위 5개 국가를 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.EXP_USD_AMT) AS EXP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG917M M
      ON T.CNTY_CD = M.CNTY_CD
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        MAX(CASE WHEN YY = '2026' THEN EXP_USD_AMT_SUM END) AS EXP_2026,
        MAX(CASE WHEN YY = '2025' THEN EXP_USD_AMT_SUM END) AS EXP_2025
    FROM BASE
    GROUP BY
        CNTY_CD,
        CNTY_NM
),
CALC AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        EXP_2026,
        EXP_2025,
        ((EXP_2026 - EXP_2025) / NULLIF(EXP_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE EXP_2025 > 0
)
SELECT
    CNTY_CD AS "국가코드",
    CNTY_NM AS "국가명",
    EXP_2026 AS "2026년수출금액",
    EXP_2025 AS "2025년수출금액",
    INC_RATE AS "증가율(%)"
FROM CALC
ORDER BY INC_RATE DESC NULLS LAST
FETCH FIRST 5 ROWS ONLY;


Example 4
Question:
2026년 기준 전년대비 국가별 무역수지 증감률을 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.EXP_USD_AMT) AS EXP_USD_AMT_SUM,
        SUM(T.IMP_USD_AMT) AS IMP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG917M M
      ON T.CNTY_CD = M.CNTY_CD
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.CNTY_CD,
        M.CNTY_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        MAX(CASE WHEN YY = '2026' THEN (EXP_USD_AMT_SUM - IMP_USD_AMT_SUM) END) AS BAL_2026,
        MAX(CASE WHEN YY = '2025' THEN (EXP_USD_AMT_SUM - IMP_USD_AMT_SUM) END) AS BAL_2025
    FROM BASE
    GROUP BY
        CNTY_CD,
        CNTY_NM
)
SELECT
    CNTY_CD AS "국가코드",
    CNTY_NM AS "국가명",
    BAL_2026 AS "2026년무역수지",
    BAL_2025 AS "2025년무역수지",
    ((BAL_2026 - BAL_2025) / NULLIF(BAL_2025, 0)) * 100 AS "증감률(%)"
FROM PIVOTED
ORDER BY "증감률(%)" DESC NULLS LAST
FETCH FIRST 200 ROWS ONLY;


Example 5
Question:
2026년 기준 전년동기대비 2단위 품목별 수입금액 증감률 상위 10개를 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.HS2_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.IMP_USD_AMT) AS IMP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS2_SGN = H.HS_SGN
     AND H.HS_LEVEL = '02'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.HS2_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS2_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN IMP_USD_AMT_SUM END) AS IMP_2026,
        MAX(CASE WHEN YY = '2025' THEN IMP_USD_AMT_SUM END) AS IMP_2025
    FROM BASE
    GROUP BY
        HS2_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS2_SGN,
        HS_NM,
        IMP_2026,
        IMP_2025,
        ((IMP_2026 - IMP_2025) / NULLIF(IMP_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE IMP_2025 > 0
)
SELECT
    HS2_SGN AS "품목2단위코드",
    HS_NM AS "품목명",
    IMP_2026 AS "2026년수입금액",
    IMP_2025 AS "2025년수입금액",
    INC_RATE AS "증감률(%)"
FROM CALC
ORDER BY INC_RATE DESC NULLS LAST
FETCH FIRST 10 ROWS ONLY;


Example 6
Question:
2026년 기준 전년동기대비 자동차 수입금액 증감률을 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.HS2_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.IMP_USD_AMT) AS IMP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS2_SGN = H.HS_SGN
     AND H.HS_LEVEL = '02'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
      AND T.HS2_SGN = '87'
    GROUP BY
        T.HS2_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS2_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN IMP_USD_AMT_SUM END) AS IMP_2026,
        MAX(CASE WHEN YY = '2025' THEN IMP_USD_AMT_SUM END) AS IMP_2025
    FROM BASE
    GROUP BY
        HS2_SGN,
        HS_NM
)
SELECT
    HS2_SGN AS "품목2단위코드",
    HS_NM AS "품목명",
    IMP_2026 AS "2026년수입금액",
    IMP_2025 AS "2025년수입금액",
    ((IMP_2026 - IMP_2025) / NULLIF(IMP_2025, 0)) * 100 AS "증감률(%)"
FROM PIVOTED
ORDER BY "증감률(%)" DESC NULLS LAST
FETCH FIRST 200 ROWS ONLY;


Anti-Pattern:
- 아래와 같은 형태는 사용하지 않는다.

Bad SQL 1:
SELECT
    ...,
    ((CURR_VAL - PREV_VAL) / PREV_VAL) * 100 AS INC_RATE
FROM ...
ORDER BY INC_RATE DESC;

Reason:
- PREV_VAL = 0 이면 0으로 나누기 오류 가능

Bad SQL 2:
SELECT ...
FROM ...
GROUP BY ...
HAVING RANK() OVER (ORDER BY INC_RATE DESC) = 3;

Reason:
- Oracle에서 analytic function을 HAVING에서 직접 사용할 수 없음

Bad SQL 3:
SELECT
    ...
FROM ...
ORDER BY INC_RATE DESC
FETCH FIRST 3 ROWS ONLY;

Reason:
- 질문이 "3위" 인데 상위 3건 조회로 잘못 해석될 수 있음
- "3위" 는 반드시 RNK = 3 형태로 처리해야 함