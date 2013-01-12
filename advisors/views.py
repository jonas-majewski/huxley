from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import render_to_response
from django.template import Context, RequestContext
from django.utils import simplejson

from core.models import *


# Dispatch to the appropriate view per the request.
def dispatch(request, page='welcome'):
    context = RequestContext(request)
    if not request.user.is_authenticated():
        return render_to_response('auth.html', context_instance=context)

    try:
        views = {'welcome': welcome,
                 'preferences': preferences,
                 'roster': roster,
                 'attendance': attendance,
                 'help': help,
                 'bugs': bugs}
        
        # Call the appropriate view function from the dictionary.
        return views[page](request, request.user.advisor_profile, context)
    # No such view exists.
    except KeyError:
        return HttpResponseNotFound()
    # The profile doesn't exist, meaning user isn't an advisor.
    except ObjectDoesNotExist:
        return HttpResponse(status=403)


# Display and/or edit the advisor's profile information.
def welcome(request, profile, context):
    school = profile.school
    if request.method == 'GET':
        return render_to_response('welcome.html',
                                  {'school': school},
                                  context_instance=context)
    elif request.method == 'POST':
        # TODO (wchieng): refactor this into a Django form.
        request.user.first_name = request.POST.get('firstname')
        request.user.last_name = request.POST.get('lastname')
        request.user.save();
        school.name = request.POST.get('schoolname')
        school.address = request.POST.get('address')
        school.city = request.POST.get('city')
        school.zip = request.POST.get('zip')
        school.programtype = request.POST.get('programtype')
        school.timesattended = request.POST.get('attendance')
        school.primaryname = request.POST.get('primaryname')
        school.primaryemail = request.POST.get('primaryemail')
        school.primaryphone = request.POST.get('primaryphone')
        school.secondaryname = request.POST.get('secname')
        school.secondaryemail = request.POST.get('secemail')
        school.secondaryphone = request.POST.get('secphone')
        school.mindelegationsize = request.POST.get('minDel')
        school.maxdelegationsize = request.POST.get('maxDel')
        school.save();
        
        return HttpResponse(status=200)
        


# Display and/or update the advisor's country/committee preferences.
def preferences(request, profile, context):
    school = profile.school
    if request.method == 'GET':
        countries = Country.objects.filter(special=False).order_by('name')
        countryprefs = school.countrypreferences.all() \
                             .order_by("countrypreference__rank")
        
        # Split the committees into pairs for double-columning in the template.
        committees = Committee.objects.filter(special=True)
        committees = [committees[i:i+2] for i in range(0, len(committees), 2)]
        committeeprefs = school.committeepreferences.all()
        return render_to_response('preferences.html',
                                  {'countryprefs': countryprefs,
                                   'countries': countries,
                                   'committees': committees,
                                   'committeeprefs':committeeprefs},
                                  context_instance=context)
    elif request.method == 'POST':
        prefs = school.countrypreferences.all()
        commprefs = school.committeepreferences.all() 
        committees = Committee.objects.filter(special=True)
        
        cprefs = []
        for index in range(0,10):
            cprefs.append(request.POST.get('CountryPref'+str(index+1)))
        cprefs = filter((lambda p: p != "NULL"), cprefs)

        countrylist = []
        alreadyDone = set();
        for countryid in cprefs:
            if countryid not in alreadyDone:
                alreadyDone.add(countryid)
                countrylist.append(Country.objects.get(id=countryid))
        
        # Delete old prefs and create new ones
        school.countrypreferences.clear()
        print "school prefs:", school.countrypreferences.all()
        for country in countrylist:
            CountryPreference.objects.create(school=school,
                                             country=country,
                                             rank=countrylist.index(country) + 1)
        
        # Deal with committee preferences now
        school.committeepreferences.clear()
        for comm in committees:
            if comm.name in request.POST:
                print "Adding committee:", comm
                school.committeepreferences.add(comm)
            
        school.save()
        return HttpResponse(status=200)


# Display the advisor's editable roster.
def roster(request, profile, context):
    if request.method == 'GET':
        c = Context()
        school = profile.school
        slots = DelegateSlot.objects.filter(assignment__school=school).order_by('assignment__committee__name')
        c.update({'slots':slots})
        return render_to_response('roster_edit.html', c, context_instance=context)

    elif request.method == 'POST':
        slot_data = simplejson.loads(request.POST['delegates'])
        for slot_id, delegate_data in slot_data.items():
            slot = DelegateSlot.objects.get(id=slot_id)
            if 'name' in delegate_data and 'email' in delegate_data:
                try:
                    delegate = slot.delegate
                    delegate.name = delegate_data['name']
                    delegate.email = delegate_data['email']
                    delegate.save()
                except:
                    Delegate.objects.create(
                        name=delegate_data['name'],
                        email=delegate_data['email'],
                        delegateslot=slot
                    )
            else:
                try:
                    slot.delegate.delete()
                except:
                    pass


        return HttpResponse(status=200)


# Display the advisor's attendance list.
def attendance(request, profile, context):
    school = profile.school
    attendInfo = getAttendInfo(request, school)
    return render_to_response('check-attendance.html', {'attendInfo': attendInfo}, context_instance=context)


# Returns a dictionary containing the attendance info for a school's delegates
def getAttendInfo(request, school):
    # Get the list of delegates
    slots = DelegateSlot.objects.filter(assignment__school=school)
    delegates = [slot.parent_link for slot in slots]
    # Initialize the dictionary of delegate to attendance
    attendInfo = {}
    attendInfo[delegate] = {} for delegate in delegates
    # Now for the six sessions
    for delegate in attendInfo.keys():
        for session in xrange(1,7):
            # TODO: add "attended_session" method on delegate slot, as well as 6 booleans
            attendInfo[delegate][session] = delegate.delegateslot.attended_session(session)
    # Return
    return attendInfo


# Display a FAQ view.
def help(request, profile, context):
    c = Context()
    questions = {}
    for cat in HelpCategory.objects.all():
        questions[cat.name] = HelpQuestion.objects.filter(category=cat)
    c.update({"categories": questions})
    return render_to_response('help.html', c, context_instance=context)


# Display a bug-reporting view.
def bugs(request, profile, context):
    return render_to_response('bugs.html', context_instance=context)