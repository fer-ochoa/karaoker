from tkinter import ttk, filedialog
import tkinter as tk
from tkinter import *
from spleeter.separator import Separator
import sys
import ffmpeg
import os
import glob
from tempfile import TemporaryDirectory, mkdtemp
from urllib.request import urlopen
from urllib.parse import unquote
from bs4 import BeautifulSoup
import re
import requests
import shutil



root = tk.Tk()
inputFolder = StringVar(root)
outputFolder = StringVar(root)
inputTxt = StringVar(root)
downloadLink = StringVar(root)
barValue = IntVar(root)
tabManager = None
barValue.set(0)
tabType = ''
subtitleFileName = ''
progressBarLabelText = StringVar(root)


def downloadContent(container, urls_):
    urls = []
    urls = urls + urls_
    progressBar = ttk.Progressbar(
        container, orient=HORIZONTAL, length=300, mode='determinate', maximum=len(urls), variable=barValue)
    progressBar.grid(column=0, row=1, pady=15)

    progressBarLabel = ttk.Label(
        container, textvariable=progressBarLabelText)
    progressBarLabel.grid(
        column=0, row=2, pady=15)

    for url in urls:
        print("Url to download: ", url)
        setProgessBarLabelText(
            len(urls), "scraping page for content")
        page = urlopen(url)
        html_bytes = page.read()
        html = html_bytes.decode("utf-8")
        soup = BeautifulSoup(html, "html.parser")
        videoUrl = soup.find(href=re.compile("https?.*?\.mp4"))["href"]
        subtitleUrl = soup.find(href=re.compile("https?.*?\.ass"))["href"]
        print(videoUrl, subtitleUrl)

        setProgessBarLabelText(
            len(urls), "downloading video")
        videoFileName = unquote(videoUrl).split('/')[-1]
        print(videoFileName)
        r = requests.get(videoUrl, stream=True)
        with open(os.path.join(inputFolder.get(), videoFileName), 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)

        setProgessBarLabelText(
            len(urls), "downloading subtitles")
        global subtitleFileName
        subtitleFileName = unquote(subtitleUrl).split('/')[-1]
        print(subtitleFileName)
        r = requests.get(subtitleUrl, stream=True)
        with open(os.path.join(inputFolder.get(), subtitleFileName), 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024*1024):
                if chunk:
                    f.write(chunk)

        barValue.set(barValue.get()+1)
        root.update_idletasks()

    progressBar.destroy()
    progressBarLabel.destroy()
    progressBarLabelText.set('')
    barValue.set(0)


def setProgessBarLabelText(total, step):
    progressBarLabelText.set(
        f'Video {barValue.get()+1} of {total}: {step}')
    root.update_idletasks()


def getUrlsInTxt():
    with open(inputTxt.get()) as txt:
        urls = txt.readlines()
        return urls


def processVideos(container):
    currenTab = tabManager.tab(tabManager.select(), "text")
    if currenTab == 'Link' and downloadLink.get() != '':
        inputFolder.set(mkdtemp())
        print(inputFolder.get())
        downloadContent(container, [downloadLink.get()])
    if currenTab == 'Multi Link' and inputTxt.get() != '':
        inputFolder.set(mkdtemp())
        print(inputFolder.get())
        downloadContent(container, getUrlsInTxt())

    if checkFolders():
        filesArray = getFilesInDirectory()
        progressBar = ttk.Progressbar(
            container, orient=HORIZONTAL, length=300, mode='determinate', maximum=len(filesArray), variable=barValue)
        progressBar.grid(column=0, row=1, pady=15)

        progressBarLabel = ttk.Label(
            container, textvariable=progressBarLabelText)
        progressBarLabel.grid(
            column=0, row=2, pady=15)
        root.update_idletasks()
        for file in filesArray:
            setProgessBarLabelText(
                len(filesArray), "splitting song into tracks")
            input_filename = os.path.split(file)[1]
            input_filename_base, input_filename_extension = os.path.splitext(
                input_filename)
            with TemporaryDirectory() as tmpdir:
                separator.separate_to_file(
                    file, tmpdir, bitrate="256k", codec="flac")
                video = ffmpeg.input(file)
                bass = ffmpeg.input(
                    os.path.join(tmpdir, input_filename_base, 'bass.flac'))
                drums = ffmpeg.input(
                    os.path.join(tmpdir, input_filename_base, 'drums.flac'))
                other = ffmpeg.input(
                    os.path.join(tmpdir, input_filename_base, 'other.flac'))
                piano = ffmpeg.input(
                    os.path.join(tmpdir, input_filename_base, 'piano.flac'))
                setProgessBarLabelText(len(filesArray), "making instrumental")
                instrumental = ffmpeg.filter_(
                    (bass, drums, other, piano), 'amix', inputs=4)
                print(os.path.join(outputFolder.get(), input_filename))
                setProgessBarLabelText(
                    len(filesArray), "joining instrumental with video")
                ffmpeg.concat(video, instrumental, v=1, a=1).output(
                    os.path.join(outputFolder.get(), f'{input_filename_base}{input_filename_extension}')).run(overwrite_output=True)
                shutil.move(os.path.join(inputFolder.get(),
                                         f'{input_filename_base}.ass'), os.path.join(outputFolder.get(),
                                                                                     f'{input_filename_base}.ass'))

            barValue.set(barValue.get()+1)
            root.update_idletasks()
        progressBar.destroy()
        progressBarLabel.destroy()
        progressBarLabelText.set('')
        barValue.set(0)
        if currenTab == 'Link' and downloadLink.get() != '':
            shutil.rmtree(inputFolder.get())


def checkFolders():
    inputFolderIsValid = type(inputFolder.get()) == str and len(
        inputFolder.get()) != 0
    outputFolderIsValid = type(outputFolder.get()) == str and len(
        outputFolder.get()) != 0
    if(inputFolderIsValid and outputFolderIsValid):
        return True


def getFilesInDirectory():
    print(f"Videos in {inputFolder.get()}:")
    print(glob.glob(os.path.join(inputFolder.get(), '*.mp4')))
    return glob.glob(os.path.join(inputFolder.get(), '*.mp4'))


def selectInputFolder(event):
    folder = filedialog.askdirectory()
    inputFolder.set(folder)
    print(inputFolder.get())


def selectOutputFolder(event):
    folder = filedialog.askdirectory()
    outputFolder.set(folder)
    print(outputFolder.get())


def selectInputTxt(event):
    file = filedialog.askopenfilename(title="Open Text file",
                                      filetypes=(("Text Files", "*.txt"),))
    inputTxt.set(file)
    print(inputTxt.get())


def create_input_frame(container, type):

    frame = ttk.Frame(container)

    if type == 'directory':
        ttk.Label(frame, text='Source folder:').grid(
            column=0, row=0, sticky=tk.W)
        inputFolderButtonText = Entry(
            frame, width=40, state='disabled', textvariable=inputFolder)
        inputFolderButtonText.grid(column=1, row=0, sticky=tk.W)
        inputFolderButtonText.bind("<1>", selectInputFolder)
    elif type == 'link':
        ttk.Label(frame, text='KaraMoe Link:').grid(
            column=0, row=0, sticky=tk.W)
        inputFolderButtonText = Entry(
            frame, width=40, textvariable=downloadLink)
        inputFolderButtonText.grid(column=1, row=0, sticky=tk.W)
    else:
        ttk.Label(frame, text='Source txt:').grid(
            column=0, row=0, sticky=tk.W)
        inputFolderButtonText = Entry(
            frame, width=40, state='disabled', textvariable=inputTxt)
        inputFolderButtonText.grid(column=1, row=0, sticky=tk.W)
        inputFolderButtonText.bind("<1>", selectInputTxt)

    ttk.Label(frame, text='Output folder:').grid(column=0, row=1, sticky=tk.W)
    inputFolderButtonText = Entry(
        frame, width=40, state='disabled', textvariable=outputFolder)
    inputFolderButtonText.grid(column=1, row=1, sticky=tk.W)
    inputFolderButtonText.bind("<1>", selectOutputFolder)

    for widget in frame.winfo_children():
        widget.grid(padx=0, pady=5)

    return frame


def create_download_link_frame(container):
    frame = ttk.Frame(container)

    frame.columnconfigure(0, weight=0)

    ttk.Label(frame, text='KaraMoe Link:').grid(column=0, row=0, sticky=tk.W)
    inputFolderButtonText = Entry(
        frame, width=40, textvariable=downloadLink)
    inputFolderButtonText.grid(column=1, row=0, sticky=tk.W)

    return frame


def create_process_frame(container):
    frame = ttk.Frame(container)

    processButton = ttk.Button(
        frame, text='Process', command=lambda: processVideos(frame)).grid(column=0, row=0)

    return frame


def create_tab(container, type):

    frame = ttk.Frame(container)

    frame.rowconfigure(0, weight=2)
    frame.rowconfigure(1, weight=3)
    frame.columnconfigure(0, weight=1)

    input_frame = create_input_frame(frame, type)
    input_frame.grid(column=0, row=0)

    process_frame = create_process_frame(frame)
    process_frame.grid(column=0, row=1)

    return frame


def create_main_window():

    # root window

    root.title('karaoker')
    root.geometry('500x250')
    root.resizable(0, 0)
    if (sys.platform == 'win32'):
        root.attributes('-toolwindow', True)

    global tabManager
    tabManager = ttk.Notebook(root)
    tabManager.pack(expand=1, fill="both")

    directoryTab = create_tab(tabManager, 'directory')
    tabManager.add(directoryTab, text="Directory")

    singleKaramoeTab = create_tab(tabManager, 'link')
    tabManager.add(singleKaramoeTab, text="Link")

    multiKaramoeTab = create_tab(tabManager, 'multi')
    tabManager.add(multiKaramoeTab, text="Multi Link")

    root.mainloop()


if __name__ == "__main__":
    separator = Separator('spleeter:5stems')
    create_main_window()
