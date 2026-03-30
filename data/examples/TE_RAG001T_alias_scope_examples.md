Examples for TE_RAG001T Alias Scope Queries

Purpose:
- 서브쿼리(인라인 뷰) 사용 시 alias scope 오류를 줄이기 위한 예시 모음이다.
- 내부 테이블 alias(T 등)를 바깥 SELECT / GROUP BY / ORDER BY 에서 직접 참조하지 않도록 유도한다.
- 바깥 쿼리에서는 반드시 서브쿼리 alias(A 등)를 사용하도록 학습시키는 데 목적이 있다.


Rule Summary:
- 서브쿼리 내부에서 사용한 테이블 alias(T, M, H 등)는 바깥 쿼리에서 직접 참조하지 않는다.
- 바깥 쿼리에서 내부 컬럼을 참조하려면 반드시 서브쿼리 alias를 부여하고 그 alias를 사용한다.
- 인라인 뷰를 사용했다면 FROM ( ... ) A 형태로 별칭을 반드시 준다.
- 바깥 SELECT, GROUP BY, ORDER BY 에서는 A.COL 형태 또는 노출 컬럼명만 사용한다.
- Oracle에서는 alias scope 위반 시 ORA-00904 invalid identifier 오류가 발생할 수 있다.


Example 1
Question:
2026년 월별 중국의 평균수출금액 알려줘

SQL:
SELECT
    SUBSTR(A.ACPT_YYMM, 5, 2) AS "월",
    AVG(A.월합계) AS "평균수출금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        SUM(T.EXP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
      AND T.CNTY_CD = 'CN'
    GROUP BY T.ACPT_YYMM
) A
GROUP BY SUBSTR(A.ACPT_YYMM, 5, 2)
ORDER BY "월"
FETCH FIRST 200 ROWS ONLY;


Example 2
Question:
2026년 월별 중국의 평균수입금액 알려줘

SQL:
SELECT
    SUBSTR(A.ACPT_YYMM, 5, 2) AS "월",
    AVG(A.월합계) AS "평균수입금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        SUM(T.IMP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
      AND T.CNTY_CD = 'CN'
    GROUP BY T.ACPT_YYMM
) A
GROUP BY SUBSTR(A.ACPT_YYMM, 5, 2)
ORDER BY "월"
FETCH FIRST 200 ROWS ONLY;


Example 3
Question:
2026년 월별 국가별 수출금액 평균을 알려줘

SQL:
SELECT
    SUBSTR(A.ACPT_YYMM, 5, 2) AS "월",
    A.CNTY_CD AS "국가코드",
    A.CNTY_NM AS "국가명",
    AVG(A.월합계) AS "평균수출금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        T.CNTY_CD,
        M.CNTY_NM,
        SUM(T.EXP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    JOIN TE_RAG917M M
      ON T.CNTY_CD = M.CNTY_CD
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
    GROUP BY
        T.ACPT_YYMM,
        T.CNTY_CD,
        M.CNTY_NM
) A
GROUP BY
    SUBSTR(A.ACPT_YYMM, 5, 2),
    A.CNTY_CD,
    A.CNTY_NM
ORDER BY "월", "국가코드"
FETCH FIRST 200 ROWS ONLY;


Example 4
Question:
2026년 월별 2단위 품목의 평균수출금액 알려줘

SQL:
SELECT
    SUBSTR(A.ACPT_YYMM, 5, 2) AS "월",
    A.HS2_SGN AS "품목2단위코드",
    A.HS_NM AS "품목명",
    AVG(A.월합계) AS "평균수출금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        T.HS2_SGN,
        H.HS_NM,
        SUM(T.EXP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS2_SGN = H.HS_SGN
     AND H.HS_LEVEL = '02'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
    GROUP BY
        T.ACPT_YYMM,
        T.HS2_SGN,
        H.HS_NM
) A
GROUP BY
    SUBSTR(A.ACPT_YYMM, 5, 2),
    A.HS2_SGN,
    A.HS_NM
ORDER BY "월", "품목2단위코드"
FETCH FIRST 200 ROWS ONLY;


Example 5
Question:
2026년 월별 중국의 품목10단위 평균수출금액 알려줘

SQL:
SELECT
    SUBSTR(A.ACPT_YYMM, 5, 2) AS "월",
    A.HS_SGN AS "품목10단위코드",
    A.HS_NM AS "품목명",
    AVG(A.월합계) AS "평균수출금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        T.HS_SGN,
        H.HS_NM,
        SUM(T.EXP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    JOIN TE_RAG901M H
      ON T.HS_SGN = H.HS_SGN
     AND H.HS_LEVEL = '10'
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
      AND T.CNTY_CD = 'CN'
    GROUP BY
        T.ACPT_YYMM,
        T.HS_SGN,
        H.HS_NM
) A
GROUP BY
    SUBSTR(A.ACPT_YYMM, 5, 2),
    A.HS_SGN,
    A.HS_NM
ORDER BY "월", "품목10단위코드"
FETCH FIRST 200 ROWS ONLY;


Anti-Pattern:
- 아래와 같은 형태는 사용하지 않는다.

Bad SQL 1:
SELECT
    SUBSTR(T.ACPT_YYMM, 5, 2) AS "월",
    AVG(월합계) AS "평균수출금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        SUM(T.EXP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    WHERE SUBSTR(T.ACPT_YYMM, 1, 4) = '2026'
      AND T.CNTY_CD = 'CN'
    GROUP BY T.ACPT_YYMM
)
GROUP BY SUBSTR(ACPT_YYMM, 5, 2);

Reason:
- 바깥 쿼리는 내부 테이블 alias T 를 모른다.
- 서브쿼리에 alias(A)를 주고 A.ACPT_YYMM 으로 참조해야 한다.

Bad SQL 2:
SELECT
    SUBSTR(A.ACPT_YYMM, 5, 2) AS "월",
    AVG(월합계) AS "평균수출금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        SUM(T.EXP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    GROUP BY T.ACPT_YYMM
)
GROUP BY SUBSTR(A.ACPT_YYMM, 5, 2);

Reason:
- 서브쿼리 alias A 를 FROM 절에 주지 않았다.
- FROM ( ... ) A 형태가 필요하다.

Bad SQL 3:
SELECT
    SUBSTR(A.ACPT_YYMM, 5, 2) AS "월",
    AVG(A.월합계) AS "평균수출금액"
FROM (
    SELECT
        T.ACPT_YYMM,
        SUM(T.EXP_USD_AMT) AS 월합계
    FROM TE_RAG001T T
    GROUP BY T.ACPT_YYMM
) A
GROUP BY SUBSTR(T.ACPT_YYMM, 5, 2);

Reason:
- GROUP BY에서도 내부 alias T 를 쓰면 안 된다.
- 바깥 쿼리는 A 만 사용해야 한다.