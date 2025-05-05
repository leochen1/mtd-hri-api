import psycopg2, os, json, logging


### 取得環境變數
def fn_GetEnv():
    # WISE-PaaS : ATMC Cloud KPI Pg
    ensaas_services = os.getenv('ENSAAS_SERVICES')
    switchcase = ''
    if ensaas_services != None:
        switchcase = '1'
        ensaas_services = json.loads(ensaas_services)
        data_Ser = ensaas_services
        PgVar = 'postgresql'
        for i in data_Ser.keys():
            if (i.find('postgresql') != -1):
                PgVar = i
        
        if ':' in ensaas_services[PgVar][0]["credentials"]["externalHosts"]:
            os.environ['PGHOST'] = str(ensaas_services[PgVar][0]["credentials"]["externalHosts"].split(':')[0])
        else:
            os.environ['PGHOST'] = str(ensaas_services[PgVar][0]["credentials"]["externalHosts"]) 
        os.environ['PGPORT'] = str(ensaas_services[PgVar][0]['credentials']['port'])
        os.environ['PGUSER'] = str(ensaas_services[PgVar][0]['credentials']['username'])
        os.environ['PGDATABASE'] = str(ensaas_services[PgVar][0]['credentials']['database'])
        os.environ['PGPASSWORD'] = str(ensaas_services[PgVar][0]['credentials']['password'])
    else:
        # local test (atmc cloud kpi pg)
        switchcase = '2'
        os.environ['PGHOST'] = '172.22.1.73'
        os.environ['PGPORT'] = str(5432)
        os.environ['PGUSER'] = '9a0b37a2-3015-4c5d-a41c-4da343e75044'
        os.environ['PGDATABASE'] = '3993eef9-8991-43cf-b336-4bea0b33c9cf'
        os.environ['PGPASSWORD'] = 'jGlXvEEntVGaHZ0EAUCz3ifpb'

    # print
    print(' ===== SwitchCase : ' + switchcase + ' =====')
    print(' PGHOST : ' + str(os.environ.get('PGHOST')))
    print(' PGPORT : ' + str(os.environ.get('PGPORT')))
    print(' PGUSER : ' + str(os.environ.get('PGUSER')))
    print(' PGDATABASE : ' + str(os.environ.get('PGDATABASE')))
    print(' PGPASSWORD : ' + str(os.environ.get('PGPASSWORD')))


### 取得SQL查詢結果
def fn_pg_cmd(sql_cmd):
    try:
        if (os.environ['PGHOST'] == None):
            fn_GetEnv()

        TemoSQLCMD = ""
        conn = psycopg2.connect(dsn="")
        cur = conn.cursor()
        # 搜尋需要計算
        TemoSQLCMD = sql_cmd
        cur.execute(TemoSQLCMD)
        
        columns = [column[0] for column in cur.description]
        results = []
        for row in cur.fetchall():
            results.append(dict(zip(columns, row)))

        #cal_rows = cur.fetchall()
        return results
    except psycopg2.Error as e:
        logging.exception(f"PG_ERROR: {str(e.pgerror)}")
        logging.exception(f"PG_CODE: {str(e.pgcode)}")
        logging.exception(f"SQL CMD Error: {str(e.TemoSQLCMD)}")
    finally:
        if conn != None:
            conn.close()
    return

### 取得SQL查詢結果資料筆數
def fn_pg_rowcount(sql_cmd):
    try:
        if (os.environ['PGHOST'] == None):
            fn_GetEnv()

        TemoSQLCMD = ""
        conn = psycopg2.connect(dsn="")
        cur = conn.cursor()

        # 搜尋需要計算
        TemoSQLCMD = sql_cmd
        cur.execute(TemoSQLCMD)
        cal_rows = cur.rowcount
        return cal_rows
    except Exception as e:
        logging.exception(f"fn_pg_rowcount Exception: {str(e)}")
    finally:
        if conn != None:
            conn.close()
    return


### 執行SQL insert, update, delete
def fn_pg_runcmd(sql_cmd):
    try:
        if (os.environ['PGHOST'] == None):
            fn_GetEnv()

        TemoSQLCMD = ""
        conn = psycopg2.connect(dsn="")
        cur = conn.cursor()
        # 搜尋需要計算
        TemoSQLCMD = sql_cmd
        cur.execute(TemoSQLCMD)
        conn.commit()
        return True
    except psycopg2.Error as e:
        logging.exception(f"fn_pg_rowcount Exception: {str(e)}")
    finally:
        if conn != None:
            conn.close()
    return

