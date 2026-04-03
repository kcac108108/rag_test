Examples for TE_RAG001T Numeric Format Rules

Purpose:
- 숫자 출력 형식에 대한 규칙을 명확히 하기 위한 예시 모음이다.
- 콤마(천 단위 구분기호) 요청이 있을 때만 최종 SELECT에서 TO_CHAR를 사용하도록 유도한다.
- 소수점 자리수 요청은 ROUND()로 처리하고, 콤마 요청이 없는 경우 숫자형을 유지하도록 학습시키는 데 목적이 있다.


Rule Summary:
- 기본적으로 숫자 컬럼은 NUMBER 타입으로 유지한다.
- 아래 3가지 요청이 있을 때만 최종 SELECT에서 TO_CHAR를 사용한다.
  1. 단위마다 , 찍어줘
  2. 천 단위 구분기호 넣어줘
  3. 보기좋게 콤마 표시해줘
- "소수점 한자리", "소수점 둘째자리", "반올림"은 콤마 포맷 요청이 아니다.
- 소수점 자리수 요청은 ROUND()로 처리한다.
- 콤마 요청이 있을 경우에도 계산, 집계, 정렬, 순위는 숫자 상태에서 먼저 처리하고,
  마지막 SELECT 출력에서만 TO_CHAR를 적용한다.
- TO_CHAR를 사용할 때는 #### 가 발생하지 않도록 충분히 큰 포맷을 사용한다.


Example 1
Question:
2026년 국가별 수출금액 합계를 보여줘

SQL:
SELECT
    T.CNTY_CD AS "국가코드",
    M.CNTY_NM AS "국가명",
    SUM(T.EXP_USD_AMT) AS "수출금액"
FROM TE_RAG001T T
JOIN TE_RAG917M M
  ON T.CNTY_CD = M.CNTY_CD
WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
GROUP BY
    T.CNTY_CD,
    M.CNTY_NM
ORDER BY "수출금액" DESC
FETCH FIRST 200 ROWS ONLY;

Reason:
- 콤마 요청이 없으므로 숫자형 그대로 반환한다.


Example 2
Question:
2026년 국가별 수출금액 합계를 보여줘. 단위마다 , 찍어줘

SQL:
SELECT
    T.CNTY_CD AS "국가코드",
    M.CNTY_NM AS "국가명",
    TO_CHAR(SUM(T.EXP_USD_AMT), 'FM999,999,999,999,999,990') AS "수출금액"
FROM TE_RAG001T T
JOIN TE_RAG917M M
  ON T.CNTY_CD = M.CNTY_CD
WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
GROUP BY
    T.CNTY_CD,
    M.CNTY_NM
ORDER BY SUM(T.EXP_USD_AMT) DESC
FETCH FIRST 200 ROWS ONLY;

Reason:
- 콤마 요청이 있으므로 최종 출력에서만 TO_CHAR를 사용한다.
- ORDER BY는 숫자값 기준으로 수행한다.


Example 3
Question:
2026년 국가별 수출금액 합계를 보여줘. 천 단위 구분기호 넣어줘

SQL:
SELECT
    T.CNTY_CD AS "국가코드",
    M.CNTY_NM AS "국가명",
    TO_CHAR(SUM(T.EXP_USD_AMT), 'FM999,999,999,999,999,990') AS "수출금액"
FROM TE_RAG001T T
JOIN TE_RAG917M M
  ON T.CNTY_CD = M.CNTY_CD
WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
GROUP BY
    T.CNTY_CD,
    M.CNTY_NM
ORDER BY SUM(T.EXP_USD_AMT) DESC
FETCH FIRST 200 ROWS ONLY;

Reason:
- "천 단위 구분기호"는 콤마 포맷 요청이다.


Example 4
Question:
2026년 국가별 수출금액 합계를 보여줘. 보기좋게 콤마 표시해줘

SQL:
SELECT
    T.CNTY_CD AS "국가코드",
    M.CNTY_NM AS "국가명",
    TO_CHAR(SUM(T.EXP_USD_AMT), 'FM999,999,999,999,999,990') AS "수출금액"
FROM TE_RAG001T T
JOIN TE_RAG917M M
  ON T.CNTY_CD = M.CNTY_CD
WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
GROUP BY
    T.CNTY_CD,
    M.CNTY_NM
ORDER BY SUM(T.EXP_USD_AMT) DESC
FETCH FIRST 200 ROWS ONLY;

Reason:
- "콤마 표시"는 콤마 포맷 요청이다.


Example 5
Question:
2026년 국가별 수출금액 합계를 보여줘. 소수점 한자리만 표시해줘

SQL:
SELECT
    T.CNTY_CD AS "국가코드",
    M.CNTY_NM AS "국가명",
    ROUND(SUM(T.EXP_USD_AMT), 1) AS "수출금액"
FROM TE_RAG001T T
JOIN TE_RAG917M M
  ON T.CNTY_CD = M.CNTY_CD
WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
GROUP BY
    T.CNTY_CD,
    M.CNTY_NM
ORDER BY ROUND(SUM(T.EXP_USD_AMT), 1) DESC
FETCH FIRST 200 ROWS ONLY;

Reason:
- 소수점 한자리 요청은 ROUND() 처리 대상이다.
- 콤마 요청이 없으므로 TO_CHAR를 사용하지 않는다.


Example 6
Question:
2026년 국가별 수출금액 합계를 보여줘. 소수점 한자리만 표시하고 단위마다 , 찍어줘

SQL:
SELECT
    T.CNTY_CD AS "국가코드",
    M.CNTY_NM AS "국가명",
    TO_CHAR(ROUND(SUM(T.EXP_USD_AMT), 1), 'FM999,999,999,999,999,990.0') AS "수출금액"
FROM TE_RAG001T T
JOIN TE_RAG917M M
  ON T.CNTY_CD = M.CNTY_CD
WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
GROUP BY
    T.CNTY_CD,
    M.CNTY_NM
ORDER BY ROUND(SUM(T.EXP_USD_AMT), 1) DESC
FETCH FIRST 200 ROWS ONLY;

Reason:
- 소수점 한자리 + 콤마 요청이 동시에 있으므로
  계산은 ROUND()로 하고, 최종 출력에서만 큰 TO_CHAR 포맷을 적용한다.


Example 7
Question:
2026년 폴란드 hs10단위 품목 중 전년동기대비 수출금액 증감율이 가장 많이 증가한 20개 품목을 보여줘. 단위마다 , 찍어줘

SQL:
WITH BASE AS (
    SELECT
        T.HS_SGN,
        H.HS_NM,
        SUBSTR(T.ACPT_YYMM, 1, 4) AS YY,
        SUM(T.EXP_WGHT) AS EXP_WGHT_SUM,
        SUM(T.EXP_USD_AMT) AS EXP_USD_AMT_SUM
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS_SGN = H.HS_SGN
     AND H.HS_LEVEL = '10'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) IN ('2026', '2025')
      AND T.CNTY_CD = 'PL'
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
        MAX(CASE WHEN YY = '2025' THEN EXP_WGHT_SUM END) AS EXP_WGHT_2025,
        MAX(CASE WHEN YY = '2026' THEN EXP_USD_AMT_SUM END) AS EXP_USD_2026,
        MAX(CASE WHEN YY = '2025' THEN EXP_USD_AMT_SUM END) AS EXP_USD_2025
    FROM BASE
    GROUP BY
        HS_SGN,
        HS_NM
),
CALC AS (
    SELECT
        HS_SGN,
        HS_NM,
        ROUND(NVL(EXP_WGHT_2026, 0) / 1000, 0) AS EXP_WGHT_2026_TON,
        ROUND(NVL(EXP_USD_2026, 0) / 1000, 0) AS EXP_USD_2026_KUSD,
        ROUND(
            ((NVL(EXP_USD_2026, 0) - NVL(EXP_USD_2025, 0)) / NULLIF(EXP_USD_2025, 0)) * 100,
            1
        ) AS INC_RATE
    FROM PIVOTED
    WHERE EXP_USD_2025 > 0
),
RANKED AS (
    SELECT
        HS_SGN,
        HS_NM,
        EXP_WGHT_2026_TON,
        EXP_USD_2026_KUSD,
        INC_RATE,
        RANK() OVER (ORDER BY INC_RATE DESC NULLS LAST) AS RNK
    FROM CALC
)
SELECT
    RNK AS "순위",
    HS_SGN AS "품목10단위코드",
    HS_NM AS "품목명",
    TO_CHAR(EXP_WGHT_2026_TON, 'FM999,999,999,999,999,990') AS "수출중량(톤)",
    TO_CHAR(EXP_USD_2026_KUSD, 'FM999,999,999,999,999,990') AS "수출금액(천불)",
    TO_CHAR(INC_RATE, 'FM999,999,999,999,999,990.0') AS "전년동기대비증감율(%)"
FROM RANKED
WHERE RNK <= 20
ORDER BY RNK
FETCH FIRST 200 ROWS ONLY;

Reason:
- 콤마 요청이 있으므로 최종 출력에서만 TO_CHAR를 적용한다.
- 증감율은 ROUND(..., 1)로 계산한 뒤 큰 TO_CHAR 포맷으로 표시한다.


Anti-Pattern:
Bad SQL 1:
SELECT
    TO_CHAR(SUM(T.EXP_USD_AMT), 'FM999,990')
FROM TE_RAG001T T;

Reason:
- 작은 포맷은 큰 값에서 #### 를 유발할 수 있다.

Bad SQL 2:
SELECT
    TO_CHAR(ROUND(SUM(T.EXP_USD_AMT), 1), 'FM999,999,990.0')
FROM TE_RAG001T T;

Reason:
- 포맷 자리수가 충분히 크지 않으면 overflow가 발생할 수 있다.

Bad SQL 3:
SELECT
    ROUND(SUM(T.EXP_USD_AMT), 1)
FROM TE_RAG001T T;

Reason:
- 이 자체는 틀리지 않지만, 콤마 요청이 있는 경우에는 최종 출력에서 TO_CHAR가 필요하다.

Bad SQL 4:
SELECT
    TO_CHAR(SUM(T.EXP_USD_AMT), 'FM999,999,999,999,999,990')
FROM TE_RAG001T T
ORDER BY 1 DESC;

Reason:
- 포맷된 문자열 기준 정렬이 될 수 있다.
- 정렬은 숫자 상태에서 먼저 수행해야 한다.