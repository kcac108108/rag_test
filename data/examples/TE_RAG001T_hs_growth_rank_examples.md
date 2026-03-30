Examples for TE_RAG001T HS Growth Rate Rank Queries

Purpose:
- 품목(HS 코드) + 증감률 + 순위가 동시에 포함된 질문에 대해
  올바른 Oracle SQL 패턴을 유도하기 위한 예시 모음이다.
- 특히 HS 코드 레벨별 조인, 전년대비/전년동기대비 증감률 계산,
  0으로 나누기 방지, NULL 처리, 순위 계산 규칙을 학습시키는 데 목적이 있다.


Rule Summary:
- 증감률 계산 시 분모가 되는 이전값은 반드시 NULLIF(이전값, 0) 또는 이전값 > 0 조건으로 보호한다.
- 순위 계산 시 NULL 증감률은 상위에 오면 안 되므로 DESC NULLS LAST를 사용한다.
- Oracle에서는 RANK() / DENSE_RANK() / ROW_NUMBER()를 WHERE 또는 HAVING에서 직접 사용하지 않는다.
- 순위 질의는 반드시 CTE 또는 서브쿼리로 한 번 감싼 후 바깥에서 WHERE RNK = N 형태로 필터링한다.
- 품목명 조회 시 TE_RAG901M과 조인한다.
- 2단위 품목은 HS2_SGN + HS_LEVEL='02'
- 4단위 품목은 HS4_SGN + HS_LEVEL='04'
- 6단위 품목은 HS6_SGN + HS_LEVEL='06'
- 10단위 품목은 HS_SGN + HS_LEVEL='10'


Example 1
Question:
2026년 기준 전년동기대비 2단위 품목별 수입금액 증감률 3위 품목은 무엇인가

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
),
RANKED AS (
    SELECT
        HS2_SGN,
        HS_NM,
        IMP_2026,
        IMP_2025,
        INC_RATE,
        RANK() OVER (ORDER BY INC_RATE DESC NULLS LAST) AS RNK
    FROM CALC
)
SELECT
    HS2_SGN AS "품목2단위코드",
    HS_NM AS "품목명",
    IMP_2026 AS "2026년수입금액",
    IMP_2025 AS "2025년수입금액",
    INC_RATE AS "증감률(%)"
FROM RANKED
WHERE RNK = 3
FETCH FIRST 200 ROWS ONLY;


Example 2
Question:
2026년 기준 전년대비 4단위 품목별 수출금액 증가율 상위 5개를 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.HS4_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.EXP_USD_AMT) AS EXP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS4_SGN = H.HS_SGN
     AND H.HS_LEVEL = '04'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.HS4_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS4_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN EXP_USD_AMT_SUM END) AS EXP_2026,
        MAX(CASE WHEN YY = '2025' THEN EXP_USD_AMT_SUM END) AS EXP_2025
    FROM BASE
    GROUP BY
        HS4_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS4_SGN,
        HS_NM,
        EXP_2026,
        EXP_2025,
        ((EXP_2026 - EXP_2025) / NULLIF(EXP_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE EXP_2025 > 0
)
SELECT
    HS4_SGN AS "품목4단위코드",
    HS_NM AS "품목명",
    EXP_2026 AS "2026년수출금액",
    EXP_2025 AS "2025년수출금액",
    INC_RATE AS "증가율(%)"
FROM CALC
ORDER BY INC_RATE DESC NULLS LAST
FETCH FIRST 5 ROWS ONLY;


Example 3
Question:
2026년 기준 전년동기대비 6단위 품목별 수입중량 증감률 2위 품목은 무엇인가

SQL:
WITH BASE AS (
    SELECT
        T.HS6_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.IMP_WGHT) AS IMP_WGHT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS6_SGN = H.HS_SGN
     AND H.HS_LEVEL = '06'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.HS6_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS6_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN IMP_WGHT_SUM END) AS IMP_WGHT_2026,
        MAX(CASE WHEN YY = '2025' THEN IMP_WGHT_SUM END) AS IMP_WGHT_2025
    FROM BASE
    GROUP BY
        HS6_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS6_SGN,
        HS_NM,
        IMP_WGHT_2026,
        IMP_WGHT_2025,
        ((IMP_WGHT_2026 - IMP_WGHT_2025) / NULLIF(IMP_WGHT_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE IMP_WGHT_2025 > 0
),
RANKED AS (
    SELECT
        HS6_SGN,
        HS_NM,
        IMP_WGHT_2026,
        IMP_WGHT_2025,
        INC_RATE,
        RANK() OVER (ORDER BY INC_RATE DESC NULLS LAST) AS RNK
    FROM CALC
)
SELECT
    HS6_SGN AS "품목6단위코드",
    HS_NM AS "품목명",
    IMP_WGHT_2026 AS "2026년수입중량",
    IMP_WGHT_2025 AS "2025년수입중량",
    INC_RATE AS "증감률(%)"
FROM RANKED
WHERE RNK = 2
FETCH FIRST 200 ROWS ONLY;


Example 4
Question:
2026년 기준 전년대비 10단위 품목별 수출중량 증가율 상위 10개를 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.HS_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.EXP_WGHT) AS EXP_WGHT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS_SGN = H.HS_SGN
     AND H.HS_LEVEL = '10'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
    GROUP BY
        T.HS_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN EXP_WGHT_SUM END) AS EXP_WGHT_2026,
        MAX(CASE WHEN YY = '2025' THEN EXP_WGHT_SUM END) AS EXP_WGHT_2025
    FROM BASE
    GROUP BY
        HS_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS_SGN,
        HS_NM,
        EXP_WGHT_2026,
        EXP_WGHT_2025,
        ((EXP_WGHT_2026 - EXP_WGHT_2025) / NULLIF(EXP_WGHT_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE EXP_WGHT_2025 > 0
)
SELECT
    HS_SGN AS "품목10단위코드",
    HS_NM AS "품목명",
    EXP_WGHT_2026 AS "2026년수출중량",
    EXP_WGHT_2025 AS "2025년수출중량",
    INC_RATE AS "증가율(%)"
FROM CALC
ORDER BY INC_RATE DESC NULLS LAST
FETCH FIRST 10 ROWS ONLY;


Example 5
Question:
2026년 기준 전년동기대비 자동차 4단위 품목별 수입금액 증감률 순위를 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.HS4_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.IMP_USD_AMT) AS IMP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS4_SGN = H.HS_SGN
     AND H.HS_LEVEL = '04'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
      AND T.HS2_SGN = '87'
    GROUP BY
        T.HS4_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS4_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN IMP_USD_AMT_SUM END) AS IMP_2026,
        MAX(CASE WHEN YY = '2025' THEN IMP_USD_AMT_SUM END) AS IMP_2025
    FROM BASE
    GROUP BY
        HS4_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS4_SGN,
        HS_NM,
        IMP_2026,
        IMP_2025,
        ((IMP_2026 - IMP_2025) / NULLIF(IMP_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE IMP_2025 > 0
),
RANKED AS (
    SELECT
        HS4_SGN,
        HS_NM,
        IMP_2026,
        IMP_2025,
        INC_RATE,
        RANK() OVER (ORDER BY INC_RATE DESC NULLS LAST) AS RNK
    FROM CALC
)
SELECT
    HS4_SGN AS "품목4단위코드",
    HS_NM AS "품목명",
    IMP_2026 AS "2026년수입금액",
    IMP_2025 AS "2025년수입금액",
    INC_RATE AS "증감률(%)",
    RNK AS "순위"
FROM RANKED
ORDER BY RNK
FETCH FIRST 200 ROWS ONLY;


Example 6
Question:
2026년 기준 전년대비 스마트폰 수출금액 증감률 1위 국가는 어디인가

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
      AND T.HS_SGN = '8517130000'
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
),
RANKED AS (
    SELECT
        CNTY_CD,
        CNTY_NM,
        EXP_2026,
        EXP_2025,
        INC_RATE,
        RANK() OVER (ORDER BY INC_RATE DESC NULLS LAST) AS RNK
    FROM CALC
)
SELECT
    CNTY_CD AS "국가코드",
    CNTY_NM AS "국가명",
    EXP_2026 AS "2026년수출금액",
    EXP_2025 AS "2025년수출금액",
    INC_RATE AS "증감률(%)"
FROM RANKED
WHERE RNK = 1
FETCH FIRST 200 ROWS ONLY;


Example 7
Question:
2026년 기준 전년동기대비 중국의 6단위 품목별 수입금액 증감률 상위 10개를 보여줘

SQL:
WITH BASE AS (
    SELECT
        T.HS6_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.IMP_USD_AMT) AS IMP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS6_SGN = H.HS_SGN
     AND H.HS_LEVEL = '06'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
      AND T.CNTY_CD = 'CN'
    GROUP BY
        T.HS6_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS6_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN IMP_USD_AMT_SUM END) AS IMP_2026,
        MAX(CASE WHEN YY = '2025' THEN IMP_USD_AMT_SUM END) AS IMP_2025
    FROM BASE
    GROUP BY
        HS6_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS6_SGN,
        HS_NM,
        IMP_2026,
        IMP_2025,
        ((IMP_2026 - IMP_2025) / NULLIF(IMP_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE IMP_2025 > 0
)
SELECT
    HS6_SGN AS "품목6단위코드",
    HS_NM AS "품목명",
    IMP_2026 AS "2026년수입금액",
    IMP_2025 AS "2025년수입금액",
    INC_RATE AS "증감률(%)"
FROM CALC
ORDER BY INC_RATE DESC NULLS LAST
FETCH FIRST 10 ROWS ONLY;


Example 8
Question:
2026년 기준 전년대비 자동차 품목 중 수출금액 증가율 3위 10단위 품목은 무엇인가

SQL:
WITH BASE AS (
    SELECT
        T.HS_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.EXP_USD_AMT) AS EXP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS_SGN = H.HS_SGN
     AND H.HS_LEVEL = '10'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
      AND T.HS2_SGN = '87'
    GROUP BY
        T.HS_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4)
),
PIVOTED AS (
    SELECT
        HS_SGN,
        HS_NM,
        MAX(CASE WHEN YY = '2026' THEN EXP_USD_AMT_SUM END) AS EXP_2026,
        MAX(CASE WHEN YY = '2025' THEN EXP_USD_AMT_SUM END) AS EXP_2025
    FROM BASE
    GROUP BY
        HS_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS_SGN,
        HS_NM,
        EXP_2026,
        EXP_2025,
        ((EXP_2026 - EXP_2025) / NULLIF(EXP_2025, 0)) * 100 AS INC_RATE
    FROM PIVOTED
    WHERE EXP_2025 > 0
),
RANKED AS (
    SELECT
        HS_SGN,
        HS_NM,
        EXP_2026,
        EXP_2025,
        INC_RATE,
        RANK() OVER (ORDER BY INC_RATE DESC NULLS LAST) AS RNK
    FROM CALC
)
SELECT
    HS_SGN AS "품목10단위코드",
    HS_NM AS "품목명",
    EXP_2026 AS "2026년수출금액",
    EXP_2025 AS "2025년수출금액",
    INC_RATE AS "증가율(%)"
FROM RANKED
WHERE RNK = 3
FETCH FIRST 200 ROWS ONLY;


Anti-Pattern:
- 아래와 같은 형태는 사용하지 않는다.

Bad SQL 1:
SELECT
    HS2_SGN,
    HS_NM,
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

Bad SQL 4:
SELECT
    ...
FROM ...
ORDER BY INC_RATE DESC;

Reason:
- NULL 증감률이 상위에 섞일 수 있음
- 반드시 DESC NULLS LAST 사용 권장

Bad SQL 5:
SELECT
    ...
FROM CALC
WHERE RNK = 3;

Reason:
- RNK는 CALC 단계에 없음
- 반드시 RANKED 단계에서 생성 후 바깥 SELECT에서 필터링해야 함