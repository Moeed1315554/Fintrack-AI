import sqlite3
import numpy as np


class target:
    def __init__(self, email):
        self.email = email

    def monthly_target(self, GA):
        conn = sqlite3.connect("fintrackai.db")
        cur  = conn.cursor()

        # Columns match DB exactly:
        # INCOMEPROFILE : ADDITIONAL_MONTHLY_INCOME, MONTHLY_INCOME, DEPENDANTS
        # EXPENSEPROFILE: GROCERIES, TRAVEL, MEDFIT, LEP, MONTHLY_RENT,
        #                 M_BILLS, FASHION, ENTERTAINMENT, EDUCATION, EMSAVING, MISCELLANEOUS
        cur.execute('''
            SELECT
                ip.ADDITIONAL_MONTHLY_INCOME,
                ip.MONTHLY_INCOME,
                ep.GROCERIES,
                ep.TRAVEL,
                ep.MEDFIT,
                ep.LEP,
                ep.MONTHLY_RENT,
                ep.M_BILLS,
                ep.FASHION,
                ep.ENTERTAINMENT,
                ep.EDUCATION,
                ep.EMSAVING,
                ep.MISCELLANEOUS,
                ip.DEPENDANTS
            FROM USER u
            JOIN INCOMEPROFILE  ip USING(USER_ID)
            JOIN EXPENSEPROFILE ep USING(USER_ID)
            WHERE u.EMAIL = ?
              AND ip.USER_ID IS NOT NULL
              AND ep.USER_ID IS NOT NULL
        ''', (self.email,))

        dt = cur.fetchall()

        if not dt:
            return 0, 0

        dt          = np.array(dt, dtype=float)
        mean_values = np.mean(dt, axis=0)

        if len(mean_values) != 14:
            return 0, 0

        (ami, mi, g, t, mf, lep, r, bills, f, en, ed, es, m, d) = mean_values

        i = mi + ami
        e = g + t + mf + lep + r + bills + f + en + ed + es + m

        if i == 0:
            return 0, 0

        n  = i - e
        Fd = 1 - min(0.03 * d, 0.18)
        Nd = n * Fd

        ratio = n / i
        if ratio < 0.15:
            behavior = 0.3
        elif ratio < 0.3:
            behavior = 0.2
        else:
            behavior = 0.1

        S0 = Nd * (1 - behavior)

        Ef = lep + r + bills + mf + ed
        rf = Ef / i

        if rf >= 0.6:
            Ff = 0.85
        elif rf >= 0.4:
            Ff = 0.92
        else:
            Ff = 1.0

        S1 = S0 * Ff

        # Expense history — only for rows with a valid USER_ID
        cur.execute('''
            SELECT CREATED_AT,
                   GROCERIES + TRAVEL + MEDFIT + LEP + MONTHLY_RENT +
                   M_BILLS + FASHION + ENTERTAINMENT + EDUCATION +
                   EMSAVING + MISCELLANEOUS
            FROM EXPENSEPROFILE
            WHERE USER_ID = (
                SELECT USER_ID FROM USER WHERE EMAIL = ?
            )
            ORDER BY CREATED_AT ASC
        ''', (self.email,))

        rows = cur.fetchall()
        conn.close()

        if not rows:
            return 0, 0

        monthly_expense = [row[1] for row in rows]
        mn  = sum(monthly_expense) / len(monthly_expense)
        std = np.std(monthly_expense)

        if mn == 0:
            return 0, 0

        v  = std / mn
        fv = max(0.8, 1 - 0.5 * v)
        S2 = S1 * fv

        # Goal tracker factor
        rt = self.goal_tracker()

        if isinstance(rt, int):
            fc = 1.0
        else:
            target_list, actual_list = rt
            total_target = sum(target_list)

            if total_target == 0:
                fc = 1.0
            else:
                c = sum(actual_list) / total_target
                if c >= 1.0:
                    fc = 1.05
                elif c >= 0.85:
                    fc = 1.0
                elif c >= 0.6:
                    fc = 0.9
                else:
                    fc = 0.8

        S3   = S2 * fc
        Trec = max(0.0, S3)

        if Trec == 0:
            return "Expense is higher than Income", "Cannot save"

        Mrec = int(np.ceil(GA / Trec))
        return round(Trec, 2), Mrec

    def goal_tracker(self):
        conn = sqlite3.connect("fintrackai.db")
        cur  = conn.cursor()

        cur.execute('''
            SELECT
                g.GOAL_AMOUNT,
                gh.SAVE_MONTH,
                CAST(CEIL((JULIANDAY(g.END_DATE) - JULIANDAY(g.START_DATE)) / 30.0) AS INT)
            FROM GOALS g
            JOIN GOAL_HISTORY gh ON g.GOALID = gh.GOALID
            WHERE g.USER_ID = (
                SELECT USER_ID FROM USER WHERE EMAIL = ?
            )
            AND g.GOALID = (
                SELECT MAX(GOALID)
                FROM GOALS
                WHERE USER_ID = (SELECT USER_ID FROM USER WHERE EMAIL = ?)
            )
            ORDER BY gh.CREATED_AT ASC
        ''', (self.email, self.email))

        rows = cur.fetchall()
        conn.close()

        if not rows:
            return 1  # no history → neutral factor

        GA       = rows[0][0]
        fixed_mn = rows[0][2]  # total months for the goal
        sm       = 0.0
        target_list = []
        actual_list = [row[1] for row in rows]

        for i, row in enumerate(rows):
            months_left  = max(1, fixed_mn - i)
            month_target = (GA - sm) / months_left
            sm          += row[1]
            target_list.append(month_target)

        return target_list, actual_list