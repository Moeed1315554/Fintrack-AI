class  target:
    def __init__(self,email):
        self.email = email
        pass

    def monthly_target(self): 

        ami = 0
        mi = 0
        g = 0
        t = 0
        mf = 0
        lep = 0
        r = 0
        b = 0
        f = 0
        en = 0
        ed = 0
        es = 0
        m = 0

        i = mi + ami
        e = g + t + mf + lep + r + b + f + en + ed + es + m

        n = i - e

        Fd  = 1 - min(0.03*d,0.018)
        Nd = n*Fd 

        if n/i<0.15:
            b=0.3
        elif n/i<0.3:
            b=0.2
        else:
            b=0.1
        
        S0=Nd(1-b)

        Ef=lep+r+b+mf+ed

        Rf =Ef/i

        if Rf>=0.5:
            Ff=0.85
        elif Rf>=0.4:
            Ff=0.92
        else:
            Ff=1

        S1=S0+Ff




