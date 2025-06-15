from django import forms
from .models import File, Folder

class FileUploadForm(forms.ModelForm):
    class Meta:
        model = File
        fields = ['file', 'visibility']
        widgets = {
            'file': forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': '*/*'}),
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file'].label = ''

class FolderCreateForm(forms.ModelForm):
    class Meta:
        model = Folder
        fields = ['name', 'visibility']
        widgets = {
            'visibility': forms.Select(attrs={'class': 'form-select'}),
        }

class RenameForm(forms.Form):
    name = forms.CharField(max_length=255)

class MoveForm(forms.Form):
    destination = forms.ModelChoiceField(queryset=Folder.objects.none())
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if user:
            self.fields['destination'].queryset = Folder.objects.filter(owner=user) 