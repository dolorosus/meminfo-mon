# meminfo-mon
This python script was created while i tried to get an insight into buffers, caches and so on used by Linux.

## tl;dr
With this script, you can take a look at the fill levels of the memory areas as bar graphs.

The first column shows the name of the parameter, in the second column the last value read . This is followed by the bar showing the current value and marked with an 'I' the highest value read in this session (high water mark). As last column the high water mark as numerical value.
All values are in kB.
 
The lowest bar, combines dirty pages, cache, the free and the used memory in one representation.

If meminfo-mon is called without parameters it will run 3600 passes and updates the screen every second. 
The number of counts and the refresh interval can be changed using the parameters ```-c``` and ```-i```. 
Try ```--help``` for help on parameters, try ```'h','F10' or 'F1'``` during runtime for additional explanations.

## Background, explained in a friendly way
The file system cache stores data that has been recently read or written from storage systems. This allows subsequent requests to retrieve data from the cache instead of reading it from slower storage systems. Write requests are clustered by caching, allowing them to be written to storage systems asynchronously in the background. The aggregation of many small write requests can have a beneficial effect on storage system load. However, data that has not yet been written to storage systems is lost in the event of power failures. Consistency of the file systems should be ensured due to the journaling functions of the file systems.

If memory is requested by applications, the "free memory" is used first; if further memory is requested, the cache areas are reduced and the memory "gained" is used to fulfill the request. Large cache areas are therefore not at the expense of the memory available for applications. 


## File system caching under Linux

File system caching in Linux is a mechanism that allows the kernel to cache frequently accessed data in memory for faster access. The kernel uses page cache to store recently read data from files and file system metadata.
For example, when a program reads data from a file, the kernel performs several tasks:

- checks the page cache to determine if the data is already in memory.
- If the data is in memory, the kernel simply returns the data from the cache
- Otherwise, it reads the data from the drive and stores a copy of it in the cache for future use

In addition, the kernel uses the dentries cache to store information about file system objects. These file system objects include directories and inodes.

Therefore, the page cache processes file system metadata, while the dentries cache manages file system objects.
The kernel uses a least recently used (LRU) algorithm to manage the page and dentries caches. 
In other words: When the cache is full and more data needs to be added, the kernel removes the most recently used data to make room for the new data.

## Get information about the cache.

The vmstat command provides detailed information about the virtual memory. In particular, the amount of memory used for caching is displayed:

    $ vmstat
    procs -----------memory---------- ---swap-- -----io---- -system-- ------cpu-----
    r  b   swpd   free   buff  cache   si   so    bi    bo   in   cs us sy id wa st
    2  0      0 6130448 11032 589532    0    0   672    48    2   16  1  1 98  0  0


The cache column shows the amount of memory used for file system caching in kilobytes. In addition, to get more details with the vmstat command, we can use the ```-s``` flag:


```
$ vmstat -s
8016140 K total memory
1282340 K used memory
 207744 K active memory
 711356 K inactive memory
6133536 K free memory
  11032 K buffer memory
 589232 K swap cache
2097148 K total swap
      0 K used swap
2097148 K free swap
   3458 non-nice user cpu ticks
    389 nice user cpu ticks
   3371 system cpu ticks
  60823 idle cpu ticks
  20782 IO-wait cpu ticks
      0 IRQ cpu ticks
     34 softirq cpu ticks
      0 stolen cpu ticks
 494275 pages paged in
  56168 pages paged out
      0 pages swapped in
      0 pages swapped out
 170063 interrupts
 384058 CPU context switches
1673971944 boot time
   5151 forks
```
Alternatively, we can use the free command to check the size of the file system cache memory in the system. The buff/cache column displays the memory usage in kilobytes:
```
$ free
                  total        used           free      shared      buff/cache      available
Mem:            8016140     1284652        6130952      144680          600536       6353032
Swap:           2097148           0        2097148
```

The ```-m ``` flag changes the command output values to megabytes. Specifically, the value of the buff/cache column is the sum of the values of the buffer and swap cache lines for vmstat.

## Configuring the File System Cache

We can use the sysctl command to configure the file system cache on Linux. In addition, the ```sysctl``` command can modify kernel parameters in the ```/etc/sysctl.conf``` file. This file contains system-wide kernel parameters that we can set at runtime.

### setvfs_cache_pression
With sysctl, we can also set the value of ```vm.vfs_cache_pression```, which controls the kernel's tendency to reclaim memory used for caching directory and inode objects:
```
$ sudo sysctl -w vm.vfs_cache_pression=50
vm.vfs_cache_pression = 50
```

Here we set the ```vfs_cache_pression``` value to 50 via the -w switch of sysctl. Consequently, the kernel favors inode and dentry caches over page cache. This can help improve performance on systems with a large number of files.
In particular, a higher value causes the kernel to prefer reclaiming inodes and dentries over cached memory. On the other hand, a lower value causes cached memory to be reclaimed over inodes and entries. Therefore, we can adjust the value to our needs.

## Configure swappiness

Swappiness controls how aggressively the kernel swaps memory pages. If you decrease the value of swappiness, the kernel is less likely to swap out less frequently used memory pages. Therefore, the kernel is more likely to cache these pages in RAM for faster access.
In addition, we can again use sysctl to set the v```m.swappiness``` parameter:
```
$ sudo sysctl -w vm.swappiness=15
vm.swappiness = 15
```
This command sets the value of ```vm.swappiness``` to 15. Again, lower values cause the kernel to prefer to keep more data in RAM. So higher values cause the kernel to swap more.

## Adjusting the file system cache

To adjust the file system caching to our needs, we can change several parameters:

- vm.dirty_background_ratio
- vm.dirty_background_bytes
- vm.dirty_ratio
- vm.dirty_bytes
- vm.dirty_writeback_centisecs
- vm.dirty_expire_centisecs

These parameters control the percentage of total system memory that we can use for caching. They regulate caching memory before the kernel writes dirty pages to memory. It is important to note that dirty pages are memory pages that have not yet been written to the storage system.
Let's look at the dirty_* variables on our system using the sysctl command:

```
$ sysctl -a | grep dirty
vm.dirty_background_ratio = 15
vm.dirty_background_bytes = 0
vm.dirty_ratio = 25
vm.dirty_bytes = 0
vm.dirty_expire_centisecs = 2000
vm.dirty_writeback_centisecs = 300
```
Here, the ```-a``` option shows all the variables that we can set along with their values. Then the grep command filters all ```vm.dirty_*``` variables.


### vm.dirty_background_ratio

The vm.dirty_background_ratio parameter specifies the amount of system memory as a percentage that can be filled with dirty pages before they are written to the storage system. For example, if we set the value of the vm.dirty_background_ratio parameter of a 64 GB RAM system to 10, it means that 6.4 GB of data (dirty pages) can remain in RAM before being written to memory.
Setting the value of ```vm.dirty_background_ratio``` for our system:

```
$ sudo sysctl -w vm.dirty_background_ratio=10
  vm.dirty_background_ratio = 10
 ```

Alternatively we can set the variable vm.dirty_background_bytes instead of vm.dirty_background_ratio. The *_bytes version uses the amount of memory in bytes. For example, we can set the amount of memory for dirty background caching to 512 MB:

```
$ sudo sysctl -w vm.dirty_background_bytes=511870912
```

Either a value for ```*_ratio``` __or__ for ```*_bytes``` can be specified! 


### vm.dirty_ratio

Specifically, vm.dirty_ratio is the absolute maximum amount of system memory, as a percentage, that can be filled with dirty pages before they are written to the drive. At this level, all new I/O activity is halted until dirty pages are written to memory.

Either a value for ```*_ratio``` __or__ for ```*_bytes``` can be specified!

To illustrate, we define the value for vm.dirty_ratio:


```
$ sudo sysctl -w vm.dirty_ratio=20
  vm.dirty_ratio = 20
 ```  
 
```Vm.dirty_bytes``` becomes 0 when we define a value in bytes for ```vm.dirty_ratio``` and vice versa. 

### The *_centisecs variables

Of course, in the event of a power failure, there is a risk that the data cached in the system memory will be lost. Therefore, to protect the system from data loss, the following variables determine how long and how often data is written to the storage system:

- vm.dirty_expire_centisecs
- vm.dirty_writeback_centisecs

vm.dirty_expire_centisecs manages how long data can remain in the cache before being written to the storage system. Let's set the variable to allow data to remain in the cache for 50 seconds:

```$ sudo sysctl -w vm.dirty_expire_centisecs=5000
vm.dirty_expire_centisecs = 5000
```

In this case, cached information can remain for up to 50 seconds before being written to the storage system (1s equals 100 centisecs).
In addition, vm.dirty_writeback_centisecs is the variable that specifies how often the writeback process checks whether there is data to write to the storage system. The lower the value, the higher the frequency and vice versa.

Let's configure vm.dirty_writeback_centisecs to check the cache every 8 seconds:
```
$ sudo sysctl -w vm.dirty_writeback_centisecs=800
vm.dirty_writeback_centisecs = 800
```

Again, the value of 600 centisecs corresponds to 8 seconds.

## Making changes permanent

After setting up the filesystem caching configurations at runtime, we want to make those changes permanent. We could do this by adding all changes to the /etc/sysctl.conf file.The system reads this file during boot.

However, the values could be overwritten during upgrades, so it is better to create a file in /etc/sysctl.d with our changes:

Now let's open /etc/sysctl.d/50-FilesystemCache.conf in an editor and add the previous configurations:
vm.vfs_cache_pression=50
vm.swappiness=10
vm.dirty_ratio=20
vm.dirty_background_ratio=10
vm.dirty_expire_centisecs=5000
vm.dirty_writeback_centisecs=600

The name of the file can be chosen arbitrarily, the system reads the files in alphabetically ascending order. The name can be used to control when our entries are evaluated.

To re-read all configuration files we can use sysctl again:

```
#sysctl --system
```

## Example

We can now configure the filesystem cache to suit our requirements. Let's take a Raspberry Pi as an example. SD cards have a relatively short lifetime in a normally configured RaspberryPi, because many small writes occur. With each of these writes, the file contents and the inode are rewritten. This stresses the memory card and shortens its lifetime.
The directory ```/var/log``` is notorious for this.
 
There are several workarounds e.g. keep ```/var/log``` in memory with log2ram or zram and then write regularly "in block" to the storage system. From my point of view it makes more sense to use the means provided by the operating system.

Example:
```
vm.dirty_background_bytes = 0
vm.dirty_background_ratio = 60
vm.dirty_bytes = 0
vm.dirty_expire_centisecs = 100000
vm.dirty_ratio = 40
vm.dirty_writeback_centisecs =  60000
vm.dirtytime_expire_seconds =  120000
```

A maximum of 60% of the memory can be used for dirty pages before the operating system writes them to the storage system.
If 40% of the memory is occupied with dirty pages, the system starts writing them to the storage system. 
The cache is checked every 600 seconds for pages to be written, pages older than 1200 seconds are written to the storage system.

This also means that in the worst case data on the mass storage can be 1200 seconds (20 minutes) old. 

File systems can have their own methods for triggering the operating system flusher, e.g. EXT3/4 implements its own mechanism for this.
You can use the ```commit=xxx``` parameter in /etc/fstab to specify the maximum time after which the file system is consistent.
