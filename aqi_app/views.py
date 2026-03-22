import os, json, datetime
import numpy as np
import joblib
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count
from .models import AQIReading, Station, ForecastResult

ML_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ml_model')

def _load(f):
    try: return joblib.load(os.path.join(ML_DIR, f))
    except: return None

CLF_MODEL=_load('aqi_model.pkl'); FUTURE_MODEL=_load('future_model.pkl')
FUTURE_SCALER=_load('future_scaler.pkl'); SEED_DATA=_load('seed_data.pkl')

def aqi_from_pm25(p):
    if p<=30: return int(p*1.67)
    elif p<=60: return int(50+(p-30)*1.67)
    elif p<=90: return int(100+(p-60)*1.67)
    elif p<=120: return int(150+(p-90)*1.67)
    else: return int(200+(p-120)*1.50)

def cat_from_aqi(v):
    if v<=50: return 'Good'
    elif v<=100: return 'Moderate'
    elif v<=150: return 'Poor'
    elif v<=200: return 'Very Poor'
    else: return 'Severe'

def badge(c):
    return {'Good':'good','Moderate':'moderate','Poor':'poor','Very Poor':'verypoor','Severe':'severe'}.get(c,'moderate')

def advice(c):
    return {'Good':'✅ Air is clean. Enjoy outdoor activities freely!',
            'Moderate':'🟡 Acceptable. Sensitive groups should take care.',
            'Poor':'🟠 Unhealthy for sensitive groups. Wear a mask.',
            'Very Poor':'🔴 Unhealthy for everyone. Limit outdoor time.',
            'Severe':'🟣 Hazardous! Stay indoors. Use air purifiers.'}.get(c,'')

def home(request):
    result=None; fdata={}
    if request.method=='POST':
        try:
            pm25=float(request.POST['pm25']); pm10=float(request.POST['pm10'])
            co=float(request.POST['co']); so2=float(request.POST['so2'])
            no2=float(request.POST['no2']); o3=float(request.POST['o3'])
            loc=request.POST.get('location','Unknown')
            fdata=dict(pm25=pm25,pm10=pm10,co=co,so2=so2,no2=no2,o3=o3,location=loc)
            if not CLF_MODEL:
                messages.error(request,"Run: python ml_model/train_models.py first!")
            else:
                cat=CLF_MODEL.predict(np.array([[pm25,pm10,co,so2,no2,o3]]))[0]
                val=aqi_from_pm25(pm25)
                r=AQIReading.objects.create(pm25=pm25,pm10=pm10,co=co,so2=so2,no2=no2,o3=o3,
                    predicted_category=cat,aqi_value=val,location_name=loc,source='manual',
                    user=request.user if request.user.is_authenticated else None)
                result=dict(cat=cat,val=val,badge=badge(cat),advice=advice(cat),loc=loc)
        except (ValueError,KeyError):
            messages.error(request,"Enter valid numbers for all fields.")
    return render(request,'home.html',{'result':result,'fdata':fdata,
        'recent':AQIReading.objects.all()[:6],'model_ok':bool(CLF_MODEL)})

def realtime_aqi(request):
    data=None; error=None
    cities=[
        {'name':'Mumbai','lat':19.0760,'lon':72.8777},
        {'name':'Delhi','lat':28.6139,'lon':77.2090},
        {'name':'Bengaluru','lat':12.9716,'lon':77.5946},
        {'name':'Chennai','lat':13.0827,'lon':80.2707},
        {'name':'Kolkata','lat':22.5726,'lon':88.3639},
        {'name':'Hyderabad','lat':17.3850,'lon':78.4867},
        {'name':'Pune','lat':18.5204,'lon':73.8567},
        {'name':'Ahmedabad','lat':23.0225,'lon':72.5714},
    ]
    sel=request.GET.get('city','Mumbai')
    ci=next((c for c in cities if c['name']==sel),cities[0])
    try:
        import urllib.request as ur
        url=(f"https://air-quality-api.open-meteo.com/v1/air-quality"
             f"?latitude={ci['lat']}&longitude={ci['lon']}"
             f"&hourly=pm10,pm2_5,carbon_monoxide,nitrogen_dioxide,sulphur_dioxide,ozone,european_aqi"
             f"&timezone=Asia%2FKolkata&forecast_days=1")
        with ur.urlopen(url,timeout=6) as r: raw=json.loads(r.read())
        h=raw.get('hourly',{})
        pl=h.get('pm2_5',[]); idx=next((i for i in range(len(pl)-1,-1,-1) if pl[i] is not None),0)
        pm25=pl[idx] or 0; pm10=(h.get('pm10',[])+[0])[idx] or 0
        co=((h.get('carbon_monoxide',[])+[0])[idx] or 0)/1000
        no2=(h.get('nitrogen_dioxide',[])+[0])[idx] or 0
        so2=(h.get('sulphur_dioxide',[])+[0])[idx] or 0
        o3=(h.get('ozone',[])+[0])[idx] or 0
        cat=CLF_MODEL.predict(np.array([[pm25,pm10,co,so2,no2,o3]]))[0] if CLF_MODEL else cat_from_aqi(aqi_from_pm25(pm25))
        val=aqi_from_pm25(pm25)
        AQIReading.objects.create(pm25=round(pm25,1),pm10=round(pm10,1),co=round(co,3),
            so2=round(so2,1),no2=round(no2,1),o3=round(o3,1),
            predicted_category=cat,aqi_value=val,location_name=f"{sel} (Live)",source='api',
            user=request.user if request.user.is_authenticated else None)
        times=h.get('time',[]); pm_h=h.get('pm2_5',[])
        trend=[{'t':times[i][-5:],'aqi':aqi_from_pm25(pm_h[i]),'cat':cat_from_aqi(aqi_from_pm25(pm_h[i]))}
               for i in range(len(times)) if i<len(pm_h) and pm_h[i] is not None]
        data={'city':sel,'pm25':round(pm25,1),'pm10':round(pm10,1),'co':round(co,3),
              'so2':round(so2,1),'no2':round(no2,1),'o3':round(o3,1),
              'aqi':val,'cat':cat,'badge':badge(cat),'advice':advice(cat),
              'trend':trend,'trend_json':json.dumps([{'t':x['t'],'aqi':x['aqi']} for x in trend]),
              'fetched':datetime.datetime.now().strftime('%d %b %Y, %I:%M %p')}
    except Exception as e:
        error=f"Live API unavailable. Showing demo data. ({e})"
        v=95; trend=[{'t':f'{i:02d}:00','aqi':max(20,min(200,v+int(np.random.randint(-20,20)))),'cat':'Moderate'} for i in range(24)]
        data={'city':sel,'pm25':55.2,'pm10':89.4,'co':1.2,'so2':45.0,'no2':62.3,'o3':78.1,
              'aqi':v,'cat':'Moderate','badge':'moderate','advice':advice('Moderate'),
              'trend':trend,'trend_json':json.dumps([{'t':x['t'],'aqi':x['aqi']} for x in trend]),
              'fetched':datetime.datetime.now().strftime('%d %b %Y, %I:%M %p'),'is_demo':True}
    return render(request,'realtime.html',{'data':data,'error':error,'cities':cities,'sel':sel})

def future_forecast(request):
    result=None
    if request.method=='POST':
        loc=request.POST.get('location','Unknown')
        cur=float(request.POST.get('current_aqi',80))
        if not FUTURE_MODEL:
            messages.error(request,"Run: python ml_model/train_models.py first!")
        else:
            now=datetime.datetime.now(); seed=SEED_DATA.copy(); seed[-1]=cur
            tf=[now.hour,now.month,now.weekday(),1 if now.weekday()>=5 else 0,
                seed.mean(),seed.std(),seed.max(),seed.min(),seed[-1],seed[-6:].mean()]
            feat=np.concatenate([seed,tf]).reshape(1,-1)
            preds=FUTURE_MODEL.predict(FUTURE_SCALER.transform(feat))[0]
            f24,f7,f30=round(float(preds[0]),1),round(float(preds[1]),1),round(float(preds[2]),1)
            c24,c7,c30=cat_from_aqi(f24),cat_from_aqi(f7),cat_from_aqi(f30)
            hourly=[]
            for h in range(24):
                fh=(now.hour+h)%24; rf=1.35 if fh in [8,9,18,19] else (0.75 if 1<=fh<=5 else 1.0)
                v=round(max(10,min(490,f24*rf+np.random.normal(0,6))),1)
                hourly.append({'h':(now+datetime.timedelta(hours=h)).strftime('%I %p'),'aqi':v,'cat':cat_from_aqi(v),'badge':badge(cat_from_aqi(v))})
            daily=[]
            for d in range(7):
                v=round(max(10,min(490,f7+np.random.normal(0,12))),1)
                daily.append({'d':(now+datetime.timedelta(days=d)).strftime('%a %d %b'),'aqi':v,'cat':cat_from_aqi(v),'badge':badge(cat_from_aqi(v))})
            ForecastResult.objects.create(location_name=loc,current_aqi=cur,
                forecast_24h=f24,forecast_7d=f7,forecast_30d=f30,
                category_24h=c24,category_7d=c7,category_30d=c30,
                user=request.user if request.user.is_authenticated else None)
            result={'loc':loc,'cur':cur,'cur_cat':cat_from_aqi(cur),'cur_badge':badge(cat_from_aqi(cur)),
                    'f24':f24,'c24':c24,'b24':badge(c24),'a24':advice(c24),
                    'f7':f7,'c7':c7,'b7':badge(c7),'f30':f30,'c30':c30,'b30':badge(c30),
                    'hourly':hourly,'daily':daily,
                    'hourly_json':json.dumps([{'h':x['h'],'aqi':x['aqi']} for x in hourly]),
                    'daily_json':json.dumps([{'d':x['d'],'aqi':x['aqi']} for x in daily])}
    return render(request,'future.html',{'result':result,'model_ok':bool(FUTURE_MODEL),
        'recent':ForecastResult.objects.all()[:5]})

def user_login(request):
    if request.user.is_authenticated: return redirect('dashboard')
    if request.method=='POST':
        u=authenticate(request,username=request.POST.get('username'),password=request.POST.get('password'))
        if u: login(request,u); return redirect('dashboard')
        messages.error(request,"Invalid username or password.")
    return render(request,'login.html')

def user_logout(request):
    logout(request); return redirect('login')

@login_required
def dashboard(request):
    readings=AQIReading.objects.all(); total=readings.count()
    avg=readings.aggregate(a=Avg('aqi_value'))['a'] or 0
    worst=readings.order_by('-aqi_value').first()
    cats={c:readings.filter(predicted_category=c).count() for c in ['Good','Moderate','Poor','Very Poor','Severe']}
    last30=list(reversed(list(readings[:30].values('location_name','aqi_value','predicted_category','recorded_at'))))
    clr={'Good':'#22c55e','Moderate':'#f59e0b','Poor':'#f97316','Very Poor':'#ef4444','Severe':'#7c3aed'}
    return render(request,'dashboard.html',{
        'total':total,'stations':Station.objects.count(),'avg_aqi':round(avg,1),'worst':worst,'cats':cats,
        'trend_labels':json.dumps([r['location_name'][:10] for r in last30]),
        'trend_values':json.dumps([r['aqi_value'] for r in last30]),
        'trend_colors':json.dumps([clr.get(r['predicted_category'],'#64748b') for r in last30]),
        'cat_labels':json.dumps(list(cats.keys())),'cat_values':json.dumps(list(cats.values())),
        'recent':readings[:10]})

@login_required
def search_history(request):
    readings=AQIReading.objects.all()
    q=request.GET.get('q',''); cat=request.GET.get('cat',''); src=request.GET.get('src','')
    if q: readings=readings.filter(location_name__icontains=q)
    if cat: readings=readings.filter(predicted_category=cat)
    if src: readings=readings.filter(source=src)
    return render(request,'search.html',{'readings':readings[:100],'q':q,'cat':cat,'src':src,'total':readings.count()})

@login_required
def visualisations(request):
    from django.db.models.functions import TruncDate
    readings=AQIReading.objects.all()
    cats={c:readings.filter(predicted_category=c).count() for c in ['Good','Moderate','Poor','Very Poor','Severe']}
    scatter=list(readings[:60].values('pm25','aqi_value','predicted_category'))
    sc_json=json.dumps([{'x':s['pm25'],'y':s['aqi_value'],'cat':s['predicted_category']} for s in scatter])
    daily_avg=list(readings.annotate(day=TruncDate('recorded_at')).values('day').annotate(avg=Avg('aqi_value')).order_by('day')[:14])
    avgs=readings.aggregate(pm25=Avg('pm25'),pm10=Avg('pm10'),co=Avg('co'),so2=Avg('so2'),no2=Avg('no2'),o3=Avg('o3'))
    return render(request,'visualisations.html',{
        'cat_labels':json.dumps(list(cats.keys())),'cat_values':json.dumps(list(cats.values())),
        'scatter_data':sc_json,
        'daily_labels':json.dumps([str(d['day']) for d in daily_avg]),
        'daily_vals':json.dumps([round(d['avg'],1) for d in daily_avg]),
        'avgs':avgs,'total':readings.count()})

@login_required
def manage_stations(request):
    if request.method=='POST':
        n=request.POST.get('name'); l=request.POST.get('location')
        if n and l:
            import secrets
            Station.objects.create(name=n,location=l,city=request.POST.get('city',''),
                latitude=float(request.POST.get('latitude',0) or 0),
                longitude=float(request.POST.get('longitude',0) or 0),
                api_key=secrets.token_hex(16))
            messages.success(request,f"Station '{n}' added!")
        else: messages.error(request,"Name and location required.")
    return render(request,'stations.html',{'stations':Station.objects.all()})

@login_required
def delete_station(request,pk):
    get_object_or_404(Station,pk=pk).delete(); messages.success(request,"Deleted."); return redirect('manage_stations')

@login_required
def readings_list(request):
    return render(request,'readings.html',{'readings':AQIReading.objects.all()})

@login_required
def delete_reading(request,pk):
    get_object_or_404(AQIReading,pk=pk).delete(); messages.success(request,"Deleted."); return redirect('readings_list')

@csrf_exempt
def iot_api(request):
    if request.method=='GET':
        return JsonResponse({'status':'ok','message':'POST JSON: pm25,pm10,co,so2,no2,o3 + optional api_key'})
    if request.method!='POST': return JsonResponse({'error':'POST required'},status=405)
    if not CLF_MODEL: return JsonResponse({'error':'Model not loaded'},status=503)
    try:
        body=json.loads(request.body)
        pm25=float(body['pm25']); pm10=float(body['pm10']); co=float(body['co'])
        so2=float(body['so2']); no2=float(body['no2']); o3=float(body['o3'])
        station=Station.objects.filter(api_key=body.get('api_key','')).first() if body.get('api_key') else None
        cat=CLF_MODEL.predict(np.array([[pm25,pm10,co,so2,no2,o3]]))[0]; val=aqi_from_pm25(pm25)
        AQIReading.objects.create(station=station,pm25=pm25,pm10=pm10,co=co,so2=so2,no2=no2,o3=o3,
            predicted_category=cat,aqi_value=val,
            location_name=station.name if station else 'IoT Device',source='iot')
        return JsonResponse({'status':'success','category':cat,'aqi':val,'advice':advice(cat),
            'station':station.name if station else 'Unknown','ts':datetime.datetime.now().isoformat()})
    except Exception as e: return JsonResponse({'error':str(e)},status=400)
