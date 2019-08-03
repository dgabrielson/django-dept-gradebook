#
# # -*- coding: utf-8 -*-
# from __future__ import unicode_literals, print_function
#
# import base64
# from io import StringIO
#
# from django import forms
# from django.db.utils import ProgrammingError
# from django.forms.formsets import formset_factory
# from django.forms.models import modelformset_factory
# from django.contrib.contenttypes.models import ContentType
# from django.template import Context, Template
#
#
# from classes.models import Section
# from classes.forms import CourseSectionInputWidget
#
# from students.models import Student_Registration
# from students.forms import ClasslistUploadForm as StudentClasslistUploadForm
#
#
# # from .models import *
# from .utils import marks_upload, get_grace
#
# #################################################################
#
# SCORE_SIZE = 6
# TEXT_INPUT_SIZE = 42
# SMALL_TEXTAREA_ATTRS = {"rows": 3, "cols": TEXT_INPUT_SIZE*7/8, }
#
# #################################################################
#
# class CourseSelectForm(forms.Form):
#     """
#     General course selection form.
#     """
#     Course_Section = forms.ModelChoiceField(
#                             Section.objects.active().current(grace=get_grace(),),
#                             label='Course & Section',
#                             )
#
#     def __init__(self, sections, mobile_flag, *args, **kwargs):
#         forms.Form.__init__(self, *args, **kwargs)
#
#         self.fields['Course_Section'].widget = CourseSectionInputWidget(sections,
#                 on_section_change= "document.getElementById('section-select-form').submit()")
#         if mobile_flag:
#             self.fields['Course_Section'].widget.in_between_html = '<span class="arrow"></span> <li class="select">'
#
#
# #################################################################
#
# class File_Upload_Form(forms.Form):
#     """
#     General file upload form.
#
#
#     if request.method == 'POST':
#         form = File_Upload_Form(request.POST, request.FILES)
#         if form.is_valid():
#             handle_uploaded_file(request.FILES['file'])
#             # f.name
#             # if f.multiple_chunks():
#             #   assert False, 'file is too big!'
#             # f.read()
#             return HttpResponseRedirect(...)
#     else:
#         form = File_Upload_Form()
#     """
#     file = forms.FileField(label='File to Upload')
#
#
#
#
# #################################################################
#
#
# def process_upload_marks_part1(file):
#     """
#     Processor for part 1 of the grade upload form.
#     """
#     contents = file.read()
#     # TODO: Consider modifying 'gradebook-mark-file' to actually contain
#     #   the rows from spreadsheet.sheetReader, which probe_file
#     #   has already.
#     fp = StringIO(contents)
#     id_list, assignment_list = marks_upload.probe_file(file.name, fileobj=fp)
#     return [
#             ('gradebook-mark-file', base64.encodestring(contents)),
#             ('gradebook-mark-file-name', file.name),
#             ('gradebook-mark-id_list', id_list),
#             ('gradebook-mark-assignment_list', assignment_list),
#         ]
#
#
#
# #################################################################
#
# def get_upload_marks_form_part2(section, data):
#     """
#     Generator for part 2 of the grade upload form.
#     """
#     id_list = data['gradebook-mark-id_list']
#     assignment_list = data['gradebook-mark-assignment_list']
#     name_size = TEXT_INPUT_SIZE
#
#     id_choices = [ (e,e) for e in id_list ]
#     if not id_choices:
#         # this happens when there is not a good header available.
#         return None
#
#
#     class _part2form(forms.Form):
#         """
#         Polymorphic form for grade uploads: based on available data.
#         """
#         ID_Header = forms.ChoiceField(id_choices, label='ID Field',
#                         initial=id_choices[0],
#                         help_text='(The default should be best in most cases.)',
#                         #empty_label=None,
#                         )
#
#         def __init__(self, *args, **kwargs):
#             super(_part2form, self).__init__(*args, **kwargs)
#             self.assignment_total = len(assignment_list)
#             for n in range(self.assignment_total):
#                 # TODO here: probe for existing,
#                 #   1. Autoselect Save_Assignment if it exists
#                 #   2. Autoselect initial for Type_Assignment if it exists.
#                 self.fields['Save_Assignment_%d' % n] = forms.BooleanField(
#                                 label='Save',
#                                 required=False,
#                                 )
#                 self.fields['Name_Assignment_%d' % n] = forms.CharField(
#                                 label='Name',
#                                 help_text='New names are saved.  Existing names are updated.',
#                                 max_length=50,
#                                 initial=assignment_list[n],
#                                 widget=forms.widgets.TextInput(attrs={"size": name_size, })
#                                 )
#                 task = Scored_Task.objects.get_by_name(section, assignment_list[n])
#                 initial = task.Category.Type.Name if task is not None else 'assignment'
#                 self.fields['Type_Assignment_%d' % n] = forms.ModelChoiceField(
#                                     Grade_Type.objects.filter(Active=True),
#                                     label='Type',
#                                     initial=initial,
#                                     empty_label=None,
#                                 )
#
#
#
#         def clean(self):
#             save_count = 0
#             for n in range(self.assignment_total):
#                 if self.cleaned_data['Save_Assignment_%d' % n]:
#                     save_count += 1
#             if save_count == 0:
#                 raise forms.ValidationError('You need to save at least one column of marks.')
#
#             return super(_part2form, self).clean()
#
#
#
#         def marks_info(self):
#             """
#             returns a dictionary of data suitable for passing into
#             gradebook.actions.marks_upload().
#
#             The form is assumed to be valid at this point, i.e.,
#             form.is_valid() == True has been checked *already*.
#             """
#             id_header = self.cleaned_data['ID_Header']
#             assignments = []
#             for n in range(self.assignment_total):
#                 assignments.append( (
#                     self.cleaned_data['Save_Assignment_%d' % n],
#                     self.cleaned_data['Name_Assignment_%d' % n],
#                     self.cleaned_data['Type_Assignment_%d' % n],
#                     assignment_list[n],
#                     ) )
#
#             spreadsheet = base64.decodestring(data['gradebook-mark-file'])
#             # NOTE: As per above TODO (in process_upload_marks_part1),
#             #   this may be changed to have the actual spreadsheet rows.
#             filename = data['gradebook-mark-file-name']
#
#             # remove session data
#             del data['gradebook-mark-file']
#             del data['gradebook-mark-file-name']
#             del data['gradebook-mark-id_list']
#             del data['gradebook-mark-assignment_list']
#
#             return {
#                     'id_header': id_header,
#                     'assignments': assignments,
#                     'data': spreadsheet,
#                     'filename': filename,
#                 }
#
#
#     return _part2form
#
#
# #################################################################
#
# class Assignment_Form(forms.ModelForm):
#     """
#     Assignment Create/Edit form.
#
#     This form does a bait and switch with the Category field to hide
#     the layer of abstration formed by 'Grade_Category'.
#     """
# #     Category = forms.ModelChoiceField(Grade_Type.objects.filter(Active=True),
# #                                       label='Type')
#
#     class Meta:
# #         model = Scored_Task
#         exclude = ('Active', 'Last_Updated', )
#         widgets = {
#             'Full_Marks' : forms.widgets.TextInput(attrs={"size": SCORE_SIZE, }),
#             'Description' : forms.widgets.TextInput(attrs={"size": TEXT_INPUT_SIZE, }),
#             'Notes' : forms.widgets.Textarea(attrs=SMALL_TEXTAREA_ATTRS),
#             }
#
#
#     def __init__(self, *args, **kwargs):
#         super(Assignment_Form, self).__init__(*args, **kwargs)
#         self.initial['Category'] = self.instance.Category.Type.pk
#
#
#     def clean_Category(self):
#         # map this to an actual Category object, and return that.
#         type = self.cleaned_data['Category']
#         section = self.instance.Category.Section
#         category, created_flag = Grade_Category.objects.get_or_create(
#                                     Active=True, Section=section, Type=type)
#         return category
#
#
#
#
# #################################################################
#
# class Score_Form(forms.ModelForm):
#     """
#     Score Create/Edit form.
#
#     TODO: add student and section parameters when creating.
#     """
#     class Meta:
# #         model = Student_Score
#         fields = ('Score', 'Notes', )
#         widgets = {
#             'Score' : forms.widgets.TextInput(attrs={"size": SCORE_SIZE, }),
#             'Notes' : forms.widgets.Textarea(attrs=SMALL_TEXTAREA_ATTRS),
#             }
#
#
# #################################################################
#
# class ScoreShortForm(forms.ModelForm):
#     """
#     Score Create/Edit form.
#     """
#     Score = forms.FloatField(required=False)
#
#
#     class Meta:
# #         model = Student_Score
#         #fields = ('Score', )
#         fields = ('Instance', 'Student', 'Score', )
#         widgets = {
#             'Instance': forms.widgets.HiddenInput,
#             'Score' : forms.widgets.TextInput(attrs={"size": SCORE_SIZE, "step": "0"}),
#             'Student' : forms.widgets.HiddenInput,
#             }
#
#
#     def is_valid(self, *args, **kwargs):
#         result = super(ScoreShortForm, self).is_valid(*args, **kwargs)
#         if not result:
#             id_error = self.errors.get('id', None)
#             if self.instance.id == 0 and id_error is not None:
#                 self.errors.pop('id')
#                 return self.is_bound and not bool(self.errors)
#         return result
#
#
# #################################################################
#
#
# class AuroraInfo(forms.Form):
#
#     copy_and_paste_this = forms.CharField(label='Copy This',
#                                     widget=forms.widgets.Textarea,
#                                     help_text='Right click (or Command click) and Select All, then copy.')
#
#     def __init__(self, section, *args, **kwargs):
#         kwargs['initial'] = dict(copy_and_paste_this=self.get_aurora_data(section) )
#         forms.Form.__init__(self, *args, **kwargs)
#
#
#     def get_aurora_data(self, section):
#         t = Template("{% for student, lettergrade in obj_list %}{{ student.student_number }}\t{{ lettergrade.lettergrade }}\t{{ lettergrade.comments }}\n{% endfor %}")
#         obj_list = LetterGradeForStudent.objects.get_all(section, good_standing=True,
#                                                             aurora_verified=True)
#         c = Context(dict(obj_list=obj_list))
#         return t.render(c)
#
#
# #################################################################
#
# class Delegation_Form(forms.ModelForm):
#     """
#     Delegation Create/Edit form.
#
#     Note, when saving with commit= False, do form.save() ; form.save_m2m()
#     """
#     class Meta:
# #         model = Delegation
#         fields = ('username', 'perms', )
#
#     def __init__(self, section, delegated_by, *args, **kwargs):
#         forms.ModelForm.__init__(self, *args, **kwargs)
#         self.section = section
#         self.delegated_by = delegated_by
#         # TODO: update this so that only perms assigned to the delegated_by user are shown.
#
#
#     def save(self, *args, **kwargs):
#         instance = forms.ModelForm.save(self, commit=False)
#         instance.section = self.section
#         instance.delegated_by = self.delegated_by
#         # does this do the right thing?
#         instance = forms.ModelForm.save(self, *args, **kwargs)
#         if kwargs.get('commit', False):
#             self.save_m2m()
#         return instance
#
#
# #################################################################
#
# SPREADSHEET_DOWNLOAD_FORMATS = (
#     ('csv', 'Comma Seperated Values'),
#     ('ods', 'OpenOffice Spreadsheet'),
#     ('xls', 'Microsoft Excel'),
# #    ('xlsx', 'Microsoft Excel 2007+'), # xlsx has issues with formulas.
# )
#
# class Mark_Download_Form(forms.Form):
#     """
#     Mark Download form.
#
#     """
#     aurora_verified_only = forms.BooleanField(required=False, initial=True,
#         label='Aurora Verified',
#         help_text='Include only students verified by an aurora classlist.')
#
#     format_ = forms.ChoiceField(choices=SPREADSHEET_DOWNLOAD_FORMATS,
#                                 label="Format", initial='xls', required=True)
#
#     include_formulas = forms.BooleanField(required=False, initial=True,
#         label="Use Formulas",
#         help_text='Use formulas instead of values for computed marks.')
#
#
# #################################################################
#
# class ClasslistUploadForm(StudentClasslistUploadForm):
#     """
#     Gradebook classlist upload form.
#     """
#     create_all_students = forms.BooleanField(required=False, initial=True,
#                             help_text='Even students without a valid username')
#
#
#     def __init__(self, section, *args, **kwargs):
#         override_values = kwargs.pop('override_values', {})
#         override_values['section'] = section
#         kwargs['override_values'] = override_values
#         value = super(ClasslistUploadForm, self).__init__(*args, **kwargs)
#         del self.fields['section']
#         return value
#
#
# #################################################################
