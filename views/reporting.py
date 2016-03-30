__author__ = 'epastag'

from django.shortcuts import render, redirect
from django.utils import timezone
from django.utils.cache import patch_cache_control
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import logout as auth_logout
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import HttpResponseRedirect, HttpResponse, QueryDict, JsonResponse, Http404
from django.core.urlresolvers import reverse, resolve
from django.contrib import messages
from django.contrib.sessions.models import Session
from django.db.models import Q
from django.db import connections, IntegrityError
from django import forms
from django.contrib.auth.models import Group

from BoMConfig.models import NewsItem, Alert, Header, Part, Configuration, ConfigLine,\
    PartBase, Baseline, Baseline_Revision, LinePricing, REF_CUSTOMER, REF_REQUEST, HeaderLock, SecurityPermission, ParseException,\
    REF_TECHNOLOGY, REF_PRODUCT_AREA_1, REF_PRODUCT_AREA_2, REF_CUSTOMER_NAME, REF_PROGRAM, REF_CONDITION, REF_MATERIAL_GROUP,\
    REF_PRODUCT_PKG, REF_SPUD, HeaderTimeTracker, REF_RADIO_BAND, REF_RADIO_FREQUENCY
from BoMConfig import menulisting, headerFile, footerFile, pagetitle, supportcontact
from BoMConfig.forms import HeaderForm, ConfigForm, DateForm, FileUploadForm, SubmitForm
from BoMConfig.templatetags.customtemplatetags import searchscramble
from BoMConfig.BillOfMaterials import BillOfMaterials
from BoMConfig.utils import UpRev, MassUploaderUpdate, GenerateRevisionSummary
from BoMConfig.views.landing import Default

import copy
from itertools import chain
import json
import openpyxl
from openpyxl import utils
import os
import re
from functools import cmp_to_key
import traceback


def Report(oRequest):
    return Default(oRequest, 'BoMConfig/report.html')
# end def