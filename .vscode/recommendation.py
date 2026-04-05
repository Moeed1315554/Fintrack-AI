import sqlite3
import numpy as np
class target:
    def __init__(self,email):
        self.email = email
        pass

    def monthly_target(self,GA):
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()
        cur = cur.execute(f'''
            SELECT ADDITIONAL_MONTHLY_INCOME,MONTHLY_INCOME,GROCERIES,TRAVEL,MEDFIT,LEP,
            MONTHLY_RENT,M_BILLS,FASHION,ENTERTAINMENT,EDUCATION,EMSAVING,MISCELLANEOUS,DEPENDANTS
            FROM USER JOIN INCOMEPROFILE USING(USER_ID) JOIN EXPENSEPROFILE USING(USER_ID)
            WHERE EMAIL = '{self.email}'
                          
            ''')
        dt = cur.fetchall()
        print(dt)

        ami, mi, g, t, mf, lep, r, b, f, en, ed, es, m, d = np.mean(dt,axis=0)

        i = mi + ami
        e = g + t + mf + lep + r + b + f + en + ed + es + m
        
        n = i - e

        Fd = 1 - min(0.03 * d, 0.18)
        Nd = n*Fd

        if n/i < 0.15:
            b = 0.3
        elif n/i < 0.3:
            b = 0.2
        else:
            b = 0.1

        S0 = Nd*(1-b)

        Ef = lep + r + b + mf + ed

        rf = Ef/i

        if rf >= 0.6:
            Ff = 0.85
        elif rf >= 0.4:
            Ff = 0.92
        else:
            Ff = 1    

        S1 = S0 * Ff
        cur.execute(f'''select created_at, groceries+travel+medfit+LeP+monthly_rent+m_bills+
            fashion+entertainment+education+emsaving+MISCELLANEOUS from expenseprofile
            where user_id = 
            (Select user_id from user where email = '{self.email}')
            order by created_at asc''')
        x = cur.fetchall()
        monthly_expense = []
        for i in range(len(x)):
            monthly_expense.append(x[i][1])
        
        mn = sum(monthly_expense)/len(x)
        std = np.std(monthly_expense)
        v = std/mn
        fv = max(0.8,1-0.5*v)
        s2 = S1*fv
        print(s2)
        rt = self.goal_tracker()
        if type(rt)==int:
            fc = 1
        else:
            c = sum(rt[1])/sum(rt[0])
            print(c)
            if c>=1.0:
                fc = 1.05
            elif c>=0.85 and c<1.0:
                fc = 1.0
            elif c>=0.6 and c<0.85:
                fc = 0.9
            else:
                fc = 0.8
        print(fc)
        s3 = s2*fc
        print(s3)
        Trec = max(0,s3)
        if Trec==0:
            return "Expense is higher than Income","Cant Save Much"
        Mrec = np.ceil(GA/Trec)
        print(Trec,Mrec)
        return Trec,Mrec

        


    def goal_tracker(self):
        conn = sqlite3.connect("fintrackai.db")
        cur = conn.cursor()
        cur.execute(f'''
                    SELECT 
                        GOAL_AMOUNT,SAVE_MONTH,
                            CEIL((JULIANDAY(END_DATE)-JULIANDAY(START_DATE))/30.0)
                    FROM GOALS JOIN GOAL_HISTORY USING(GOALID) 
                    WHERE GOALS.USER_ID = (Select user_id from user where email = '{self.email}')
                    AND GOALID = (Select MAX(GOALID) from  USER JOIN GOALS USING(USER_ID)
                    where email = '{self.email}')
                    ''')
        x = cur.fetchall()
        actualdm = [ i[1] for i in x]
        print(x)
        if len(x)==0:
            return 1
        GA = x[0][0]
        sm = 0
        fixedmn = x[0][-1]
        targetedmn =[] 
        for i  in range(len(x)):
            mntarget = (GA-sm)/(fixedmn-i)
            sm = sm+x[i][1]
            targetedmn.append(mntarget)
        
        return targetedmn,actualdm


ob = target('mdmoeed1315554@gmail.com')
print(ob.monthly_target(540000))