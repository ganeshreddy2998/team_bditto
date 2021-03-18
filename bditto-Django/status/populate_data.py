from django.shortcuts import render
import xlrd
from status.models import Status
from accounts.models import Profile

def populate_status(request):
    if request.method=='POST':
        file = request.FILES.get('status_data')
        excel = xlrd.open_workbook(file_contents=file.read())
        sheet=excel.sheet_by_index(0)

        profile = Profile.objects.all().first()

        for i in range(sheet.nrows):
            content = str(sheet.cell(i,0).value)

            Status.objects.create(
                author = profile,
                content = content,
                background_color = '#000000'
            )
    
    return render(request, 'upload_data.html')
        
