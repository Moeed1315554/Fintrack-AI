import sqlite3
import numpy as np


class target:
    def __init__(self, email):
        self.email = email

    def monthly_target(self, GA):
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()

        # ✅ Safe query (no injection)
        cur.execute('''
            SELECT 
                ADDITIONAL_MONTHLY_INCOME, MONTHLY_INCOME,
                GROCERIES, TRAVEL, MEDFIT, LEP,
                MONTHLY_RENT, M_BILLS, FASHION, ENTERTAINMENT,
                EDUCATION, EMSAVING, MISCELLANEOUS, DEPENDANTS
            FROM USER 
            JOIN INCOMEPROFILE USING(USER_ID) 
            JOIN EXPENSEPROFILE USING(USER_ID)
            WHERE EMAIL = ?
        ''', (self.email,))

        dt = cur.fetchall()

        # ✅ Handle empty data
        if len(dt) == 0:
            return 0, 0

        dt = np.array(dt)

        mean_values = np.mean(dt, axis=0)

        if len(mean_values) != 14:
            return 0, 0

        (
            ami, mi, g, t, mf, lep, r, bills, f, en, ed, es, m, d
        ) = mean_values

        # ✅ Income & Expense
        i = mi + ami
        e = g + t + mf + lep + r + bills + f + en + ed + es + m

        if i == 0:
            return 0, 0

        n = i - e

        # ✅ Dependents factor
        Fd = 1 - min(0.03 * d, 0.18)
        Nd = n * Fd

        # ✅ Savings behavior (fixed variable name)
        if n / i < 0.15:
            behavior = 0.3
        elif n / i < 0.3:
            behavior = 0.2
        else:
            behavior = 0.1

        S0 = Nd * (1 - behavior)

        # ✅ Fixed expenses ratio
        Ef = lep + r + bills + mf + ed
        rf = Ef / i

        if rf >= 0.6:
            Ff = 0.85
        elif rf >= 0.4:
            Ff = 0.92
        else:
            Ff = 1

        S1 = S0 * Ff

        # ✅ Expense history
        cur.execute('''
            SELECT created_at,
                   groceries + travel + medfit + lep + monthly_rent +
                   m_bills + fashion + entertainment + education +
                   emsaving + miscellaneous
            FROM expenseprofile
            WHERE user_id = (
                SELECT user_id FROM user WHERE email = ?
            )
            ORDER BY created_at ASC
        ''', (self.email,))

        x = cur.fetchall()

        if len(x) == 0:
            return 0, 0

        monthly_expense = [row[1] for row in x]

        mn = sum(monthly_expense) / len(monthly_expense)
        std = np.std(monthly_expense)

        if mn == 0:
            return 0, 0

        v = std / mn
        fv = max(0.8, 1 - 0.5 * v)

        s2 = S1 * fv

        # ✅ Goal tracking
        rt = self.goal_tracker()

        if isinstance(rt, int):
            fc = 1
        else:
            target_list, actual_list = rt

            if sum(target_list) == 0:
                fc = 1
            else:
                c = sum(actual_list) / sum(target_list)

                if c >= 1.0:
                    fc = 1.05
                elif c >= 0.85:
                    fc = 1.0
                elif c >= 0.6:
                    fc = 0.9
                else:
                    fc = 0.8

        s3 = s2 * fc

        Trec = max(0, s3)

        if Trec == 0:
            return "Expense is higher than Income", "Cannot save"

        Mrec = int(np.ceil(GA / Trec))

        return round(Trec, 2), Mrec

    def goal_tracker(self):
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()

        cur.execute('''
            SELECT 
                GOAL_AMOUNT,
                SAVE_MONTH,
                CEIL((JULIANDAY(END_DATE) - JULIANDAY(START_DATE)) / 30.0)
            FROM GOALS 
            JOIN GOAL_HISTORY USING(GOALID) 
            WHERE GOALS.USER_ID = (
                SELECT user_id FROM user WHERE email = ?
            )
            AND GOALID = (
                SELECT MAX(GOALID)
                FROM USER JOIN GOALS USING(USER_ID)
                WHERE email = ?
            )
        ''', (self.email, self.email))

        x = cur.fetchall()

        if len(x) == 0:
            return 1

        GA = x[0][0]
        sm = 0
        fixedmn = x[0][-1]

        targetedmn = []
        actualdm = [i[1] for i in x]

        for i in range(len(x)):
            mntarget = (GA - sm) / max(1, (fixedmn - i))
            sm += x[i][1]
            targetedmn.append(mntarget)

        return targetedmn, actualdm